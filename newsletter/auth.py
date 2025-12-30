from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from .models import Subscriber
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse, HttpRequest
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from .serializers import UserSerializer, SubscriberSerializer
from django.contrib.auth.models import User
import json
import uuid


def _parse_body(request: HttpRequest) -> dict:
    # if request.content_type and "application/json" in request.content_type:
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}
    # Fallback for form-encoded
    return request.POST.dict()


@ensure_csrf_cookie
def csrf_token(request: HttpRequest):
    return JsonResponse({"message": "CSRF cookie set."}, status=200)


@csrf_exempt
@require_POST
@transaction.atomic
def signup(request: HttpRequest):
    data = _parse_body(request)
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not username:
        return JsonResponse({"detail": "username is required"}, status=400)
    if not password:
        return JsonResponse({"detail": "password is required"}, status=400)
    if not email:
        return JsonResponse({"detail": "email is required"}, status=400)

    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"detail": "username already exists"}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"detail": "email already in use"}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    login(request, user)
    return JsonResponse({"Developer": "Arun Et", "user": UserSerializer(user).data}, status=201)

@csrf_exempt
@require_POST
def login_view(request: HttpRequest):
    data = _parse_body(request)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not password:
        return JsonResponse({"detail": "password is required"}, status=400)

    if not email:
        return JsonResponse({"detail": "email is required"}, status=400)

    if email:
        try:
            user_by_email = User.objects.get(email__iexact=email)
            login_identifier = user_by_email.username
        except User.DoesNotExist:
            return JsonResponse({"detail": "Invalid credentials"}, status=401)

    user = authenticate(request, username=login_identifier, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid credentials"}, status=401)

    login(request, user)
    return JsonResponse({"user": UserSerializer(user).data}, status=200)


@require_POST
def logout_view(request: HttpRequest):
    logout(request)
    return JsonResponse({"message": "Logged out"}, status=200)


@require_http_methods(["GET"])
def me(request: HttpRequest):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    return JsonResponse({"user": UserSerializer(request.user).data}, status=200)


@require_http_methods(["PATCH", "PUT"])
@transaction.atomic
def update_me(request: HttpRequest):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    data = _parse_body(request)

    new_email = (data.get("email") or "").strip().lower()
    new_first_name = (data.get("first_name") or "").strip()
    new_last_name = (data.get("last_name") or "").strip()

    user: User = request.user

    if new_email and User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
        return JsonResponse({"detail": "email already in use"}, status=400)

    if new_email:
        user.email = new_email
    if new_first_name:
        user.first_name = new_first_name
    if new_last_name:
        user.last_name = new_last_name

    user.save()
    return JsonResponse({"user": UserSerializer(user).data}, status=200)


@require_POST
@transaction.atomic
def change_password(request: HttpRequest):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)

    data = _parse_body(request)
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return JsonResponse({"detail": "old_password and new_password are required"}, status=400)

    user: User = request.user
    if not user.check_password(old_password):
        return JsonResponse({"detail": "Old password is incorrect"}, status=400)

    user.set_password(new_password)
    user.save()
    update_session_auth_hash(request, user)  # keep the user logged in
    return JsonResponse({"message": "Password updated"}, status=200)


@require_http_methods(["GET"])
@ensure_csrf_cookie
def users_list(request: HttpRequest):
    accountId = request.headers.get("accountId")
    # if not request.user.is_authenticated or not request.user.is_staff:
    #     return JsonResponse({"detail": "Forbidden"}, status=403)
    if accountId:
        users_qs = Subscriber.objects.filter(accountId=accountId).order_by("id")
    else:
        users_qs = Subscriber.objects.all().order_by("id")
    data = SubscriberSerializer(users_qs, many=True).data
    return JsonResponse({"Developer": "Arun Et", "users": data}, status=200)


@require_POST
def subscribe(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        email = data.get("email")
        name = data.get("name", "")
        accountId = data.get("accountId")
    else:
        email = request.POST.get("email")
        name = request.POST.get("name", "")
        accountId = request.POST.get("accountId")
    if not email:
        return JsonResponse({"detail": "email is required"}, status=400)

    Subscriber.objects.get_or_create(accountId=accountId, email=email, defaults={"name": name})
    return JsonResponse({"Developer": "Arun Et", "message": "Subscriber created successfully", "data": {"email": email, "name": name}}, status=201)


@require_POST
def update_subscriber(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        email = data.get("email")
        name = data.get("name")
        subscriber_id = data.get("subscriber_id")
    if not subscriber_id:
        return JsonResponse({"detail": "subscriber_id is required"}, status=400)

    Subscriber.objects.filter(id=subscriber_id).update(name=name, email=email)
    return JsonResponse({"Developer": "Arun Et", "message": "Subscriber updated successfully"}, status=200)


@require_POST
def unsubscribe(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        subscriber_id = data.get("subscriber_id")
        activeStatus = data.get("activeStatus")
    else:
        subscriber_id = request.POST.get("subscriber_id")
        activeStatus = request.POST.get("activeStatus")
    if not subscriber_id or activeStatus not in [True, False]:
        return JsonResponse({"Developer": "Arun Et", "detail": "subscriber_id and activeStatus are required"}, status=400)

    Subscriber.objects.filter(id=subscriber_id).update(is_active=activeStatus)
    return JsonResponse({"Developer": "Arun Et", "message": "Subscriber status updated successfully"}, status=200)