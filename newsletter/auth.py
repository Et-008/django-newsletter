from datetime import datetime
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from .models import Subscriber
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse, HttpRequest
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from .serializers import UserSerializer, SubscriberSerializer
from django.contrib.auth.models import User
from .crypto_utils import generate_account_id, generate_unsubscribe_token
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
    """
    List subscribers for the current user's newsletter.
    
    Headers:
        - accountId: The newsletter owner's accountId (required for filtering)
    
    Query params:
        - active_only: "true" to show only active subscribers (default: true)
        - include_inactive: "true" to include inactive subscribers
        - status: "active", "inactive", or "all" (alternative to above)
    
    Returns subscribers with their subscription status for this specific newsletter.
    """
    accountId = request.headers.get("accountId")
    
    # Determine filtering mode
    status_param = request.GET.get("status", "").lower()
    if status_param == "all":
        include_all = True
        active_only = False
    elif status_param == "inactive":
        include_all = False
        active_only = False
    elif status_param == "active":
        include_all = False
        active_only = True
    else:
        # Legacy params support
        include_inactive = request.GET.get("include_inactive", "").lower() == "true"
        active_only_param = request.GET.get("active_only", "true").lower()
        active_only = active_only_param == "true" and not include_inactive
        include_all = include_inactive
    
    if accountId:
        # Filter subscribers who have this accountId in their accountIds dict
        users_qs = Subscriber.objects.filter(accountIds__has_key=accountId).order_by("id")
        
        # Build response with subscription status for this newsletter
        result = []
        for sub in users_qs:
            account_ids = sub.accountIds or {}
            
            # Handle old list format during migration
            if isinstance(account_ids, list):
                is_active = accountId in account_ids
                subscription_info = {"active": is_active, "legacy_format": True}
            else:
                subscription_info = account_ids.get(accountId, {})
                is_active = subscription_info.get("active", True)
            
            # Apply status filter
            if active_only and not is_active:
                continue
            if not include_all and not active_only and is_active:
                # status=inactive: skip active subscribers
                continue
            
            # Serialize subscriber and add subscription info
            sub_data = SubscriberSerializer(sub).data
            sub_data["subscription"] = {
                "active": is_active,
                "subscribed_at": subscription_info.get("subscribed_at"),
                "unsubscribed_at": subscription_info.get("unsubscribed_at"),
                "resubscribed_at": subscription_info.get("resubscribed_at"),
            }
            result.append(sub_data)
        
        return JsonResponse({
            "Developer": "Arun Et",
            "users": result,
            "count": len(result),
            "filter": {
                "accountId": accountId,
                "status": "active" if active_only else ("all" if include_all else "inactive")
            }
        }, status=200)
    else:
        # No accountId: return all subscribers (admin view)
        users_qs = Subscriber.objects.all().order_by("id")
        data = SubscriberSerializer(users_qs, many=True).data
        return JsonResponse({
            "Developer": "Arun Et",
            "users": data,
            "count": len(data)
        }, status=200)


@require_POST
def subscribe(request):
    """
    Admin subscribe endpoint (authenticated users).
    Uses new accountIds dict structure for per-newsletter active status.
    """
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

    now = datetime.utcnow().isoformat() + "Z"
    
    # Try to get an existing subscriber by email
    subscriber = Subscriber.objects.filter(email=email).first()
    if not subscriber:
        # Create new subscriber with dict structure
        initial_accounts = {accountId: {"active": True, "subscribed_at": now}} if accountId else {}
        subscriber = Subscriber.objects.create(email=email, name=name, accountIds=initial_accounts)
    else:
        account_ids = subscriber.accountIds or {}
        
        # Handle migration from old list format
        if isinstance(account_ids, list):
            account_ids = {aid: {"active": True, "subscribed_at": now} for aid in account_ids}
        
        if accountId:
            if accountId in account_ids and account_ids[accountId].get("active", True):
                return JsonResponse({
                    "Developer": "Arun Et",
                    "message": "Duplicate entry",
                    "data": {"email": email, "name": name}
                }, status=409)
            else:
                # Add or reactivate subscription
                if accountId in account_ids:
                    account_ids[accountId]["active"] = True
                    account_ids[accountId]["resubscribed_at"] = now
                else:
                    account_ids[accountId] = {"active": True, "subscribed_at": now}
                subscriber.accountIds = account_ids
                subscriber.save()
        else:
            subscriber.accountIds = account_ids
            subscriber.save()
    
    return JsonResponse({
        "Developer": "Arun Et",
        "message": "Subscriber created successfully",
        "data": {"email": email, "name": name}
    }, status=201)


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
    """
    Admin endpoint to update subscriber status for a specific account.
    
    Body (JSON):
        - subscriber_id (required): The subscriber's ID
        - activeStatus (required): true/false - the new subscription status
        - accountId (optional): If provided, updates status for this specific account only.
                               If omitted, updates the global is_active field.
    
    This allows admins to:
        1. Unsubscribe/resubscribe a user from a specific account (per-account)
        2. Globally deactivate a subscriber (legacy behavior)
    """
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        subscriber_id = data.get("subscriber_id")
        activeStatus = data.get("activeStatus")
        accountId = data.get("accountId")
    else:
        subscriber_id = request.POST.get("subscriber_id")
        activeStatus = request.POST.get("activeStatus")
        accountId = request.POST.get("accountId")
    
    if not subscriber_id or activeStatus not in [True, False]:
        return JsonResponse({
            "Developer": "Arun Et",
            "detail": "subscriber_id and activeStatus are required"
        }, status=400)
    
    # Find the subscriber
    subscriber = Subscriber.objects.filter(id=subscriber_id).first()
    if not subscriber:
        return JsonResponse({
            "Developer": "Arun Et",
            "detail": "Subscriber not found"
        }, status=404)
    
    now = datetime.utcnow().isoformat() + "Z"
    
    if accountId:
        # Per-account status update
        account_ids = subscriber.accountIds or {}
        
        # Initialize entry if it doesn't exist
        if accountId not in account_ids:
            account_ids[accountId] = {"subscribed_at": now}
        
        # Update the status for this specific account
        account_ids[accountId]["active"] = activeStatus
        if activeStatus:
            account_ids[accountId]["resubscribed_at"] = now
        else:
            account_ids[accountId]["unsubscribed_at"] = now
        
        subscriber.accountIds = account_ids
        subscriber.save()
        
        return JsonResponse({
            "Developer": "Arun Et",
            "message": f"Subscriber {'resubscribed' if activeStatus else 'unsubscribed'} successfully",
            "data": {
                "subscriber_id": subscriber_id,
                "accountId": accountId,
                "active": activeStatus
            }
        }, status=200)
    else:
        # Global status update (legacy behavior)
        subscriber.is_active = activeStatus

        if not activeStatus:
            for accountId in subscriber.accountIds:
                subscriber.accountIds[accountId]["active"] = False
                subscriber.accountIds[accountId]["unsubscribed_at"] = now
        subscriber.save()
        
        return JsonResponse({
            "Developer": "Arun Et",
            "message": f"Subscriber global status updated successfully",
            "data": {
                "subscriber_id": subscriber_id,
                "is_active": activeStatus
            }
        }, status=200)


@require_http_methods(["GET"])
def get_account_id(request: HttpRequest):
    """
    Returns the accountId for the logged-in user to embed in their client website.
    This accountId is a signed token that maps subscribers to this user's account.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    
    account_id = generate_account_id(request.user.email)
    return JsonResponse({
        "Developer": "Arun Et",
        "accountId": account_id,
        "usage": "Include this accountId in the header or body when calling the subscribe API from your client website."
    }, status=200)


@require_http_methods(["GET", "POST"])
def get_unsubscribe_token(request: HttpRequest):
    """
    Generate an unsubscribe token for a specific subscriber.
    Used when composing/sending newsletters to include unsubscribe links.
    
    GET params or POST body:
        - subscriber_email (required): The subscriber's email address
    
    Returns the unsubscribe token and a ready-to-use unsubscribe URL.
    
    Email headers for one-click unsubscribe (RFC 8058):
        List-Unsubscribe: <{unsubscribe_url}>
        List-Unsubscribe-Post: List-Unsubscribe=One-Click
    """
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated"}, status=401)
    
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            subscriber_email = data.get("subscriber_email")
        except Exception:
            subscriber_email = request.POST.get("subscriber_email")
    else:
        subscriber_email = request.GET.get("subscriber_email")
    
    if not subscriber_email:
        return JsonResponse({"detail": "subscriber_email is required"}, status=400)
    
    # Generate the accountId for the current user
    account_id = generate_account_id(request.user.email)
    
    # Generate the unsubscribe token
    unsubscribe_token = generate_unsubscribe_token(subscriber_email, account_id)
    
    # Build the unsubscribe URL (you'll need to replace with your actual domain)
    # The frontend/email sender should construct the full URL
    return JsonResponse({
        "Developer": "Arun Et",
        "token": unsubscribe_token,
        "subscriber_email": subscriber_email,
        "usage": {
            "url_template": "/api/public/unsubscribe/?token={token}",
            "email_headers": {
                "List-Unsubscribe": "<https://YOUR_DOMAIN/api/public/unsubscribe/?token=" + unsubscribe_token + ">",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
            }
        }
    }, status=200)