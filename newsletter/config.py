import json
from typing import Optional

from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail.backends.smtp import EmailBackend

from .models import EmailConfig
from .serializers import EmailConfigSerializer
from .crypto_utils import decrypt_secret


def _require_auth(request: HttpRequest) -> Optional[JsonResponse]:
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required"}, status=401)
    return None


def _parse_json_body(request: HttpRequest) -> Optional[dict]:
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8"))
        except Exception:
            return None
    return None


def _get_primary_config(user) -> Optional[EmailConfig]:
    try:
        return EmailConfig.objects.filter(user=user, is_active=True).order_by("-is_primary", "-updated_at").first()
    except EmailConfig.DoesNotExist:
        return None


@require_GET
def get_config(request: HttpRequest):
    if (resp := _require_auth(request)) is not None:
        return resp

    config_id = request.GET.get("id")
    config: Optional[EmailConfig] = None
    if config_id:
        try:
            config = EmailConfig.objects.get(user=request.user, pk=int(config_id))
        except (EmailConfig.DoesNotExist, ValueError):
            return JsonResponse({"data": None}, status=200)
    else:
        config = _get_primary_config(request.user)
        if not config:
            return JsonResponse({"data": None}, status=200)

    data = EmailConfigSerializer(config).data
    return JsonResponse({"data": data}, status=200)


@require_GET
def list_configs(request: HttpRequest):
    if (resp := _require_auth(request)) is not None:
        return resp
    qs = EmailConfig.objects.filter(user=request.user).order_by("-is_primary", "-updated_at")
    data = EmailConfigSerializer(qs, many=True).data
    return JsonResponse({"data": data}, status=200)


@require_POST
@csrf_exempt
def create_config(request: HttpRequest):
    if (resp := _require_auth(request)) is not None:
        return resp
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    serializer = EmailConfigSerializer(data=payload, context={"request": request})
    if serializer.is_valid():
        obj = serializer.save()
        return JsonResponse({"data": EmailConfigSerializer(obj).data}, status=201)
    return JsonResponse({"errors": serializer.errors}, status=400)


@require_http_methods(["POST", "PATCH"])
@csrf_exempt
def update_config(request: HttpRequest):
    """
    Backward-compatible endpoint:
    - If 'id' provided in body, update that config
    - Else update current primary if exists
    - Else create a new primary using provided fields
    """
    if (resp := _require_auth(request)) is not None:
        return resp
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)

    config: Optional[EmailConfig] = None
    config_id = payload.get("id")
    if config_id:
        try:
            config = EmailConfig.objects.get(user=request.user, pk=int(config_id))
        except (EmailConfig.DoesNotExist, ValueError):
            return JsonResponse({"detail": "Config not found"}, status=404)
    else:
        config = _get_primary_config(request.user)

    if config:
        serializer = EmailConfigSerializer(config, data=payload, partial=True, context={"request": request})
        if serializer.is_valid():
            obj = serializer.save()
            return JsonResponse({"data": EmailConfigSerializer(obj).data}, status=200)
        return JsonResponse({"errors": serializer.errors}, status=400)
    else:
        # Create new primary
        payload.setdefault("is_primary", True)
        serializer = EmailConfigSerializer(data=payload, context={"request": request})
        if serializer.is_valid():
            obj = serializer.save()
            return JsonResponse({"data": EmailConfigSerializer(obj).data}, status=201)
        return JsonResponse({"errors": serializer.errors}, status=400)


@require_http_methods(["PATCH", "POST"])
@csrf_exempt
def update_config_by_id(request: HttpRequest, id: int):
    if (resp := _require_auth(request)) is not None:
        return resp
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON"}, status=400)
    try:
        config = EmailConfig.objects.get(user=request.user, pk=int(id))
    except (EmailConfig.DoesNotExist, ValueError):
        return JsonResponse({"detail": "Config not found"}, status=404)
    serializer = EmailConfigSerializer(config, data=payload, partial=True, context={"request": request})
    if serializer.is_valid():
        obj = serializer.save()
        return JsonResponse({"data": EmailConfigSerializer(obj).data}, status=200)
    return JsonResponse({"errors": serializer.errors}, status=400)


@require_POST
@csrf_exempt
def set_primary(request: HttpRequest, id: int):
    if (resp := _require_auth(request)) is not None:
        return resp
    try:
        config = EmailConfig.objects.get(user=request.user, pk=int(id))
    except (EmailConfig.DoesNotExist, ValueError):
        return JsonResponse({"detail": "Config not found"}, status=404)
    config.is_primary = True
    config.save()  # will unset others via model save()
    return JsonResponse({"data": EmailConfigSerializer(config).data}, status=200)


@require_POST
@csrf_exempt
def verify_config(request: HttpRequest, id: int):
    if (resp := _require_auth(request)) is not None:
        return resp
    try:
        config = EmailConfig.objects.get(user=request.user, pk=int(id))
    except (EmailConfig.DoesNotExist, ValueError):
        return JsonResponse({"detail": "Config not found"}, status=404)

    if config.provider != EmailConfig.PROVIDER_SMTP:
        return JsonResponse({"detail": "Only SMTP verification supported"}, status=400)

    password = decrypt_secret(config.password_encrypted) if config.password_encrypted else ""
    backend = EmailBackend(
        host=config.host,
        port=config.port,
        username=config.username,
        password=password,
        use_tls=config.use_tls,
        use_ssl=config.use_ssl,
        timeout=10,
        fail_silently=True,
    )
    ok = False
    error = None
    try:
        backend.open()
        ok = True
    except Exception as e:
        ok = False
        error = str(e)
    finally:
        try:
            backend.close()
        except Exception:
            pass

    if ok:
        config.last_verified_at = timezone.now()
        config.last_verify_error = ""
        config.save(update_fields=["last_verified_at", "last_verify_error", "updated_at"])
        return JsonResponse({"status": "ok", "verified_at": config.last_verified_at}, status=200)
    else:
        config.last_verify_error = error or "Unknown error"
        config.save(update_fields=["last_verify_error", "updated_at"])
        return JsonResponse({"status": "error", "error": config.last_verify_error}, status=400)