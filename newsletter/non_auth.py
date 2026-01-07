import json
from datetime import datetime
from django.contrib.auth.models import User
from functools import wraps
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import Subscriber
from .crypto_utils import validate_account_id, validate_unsubscribe_token


def allow_cors(view_func):
    """
    Decorator to add CORS headers allowing any origin.
    Used for public endpoints that are called from client websites.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Handle preflight OPTIONS request
        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = view_func(request, *args, **kwargs)
        
        # Add CORS headers
        origin = request.headers.get("Origin", "*")
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, accountId, Accept"
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Max-Age"] = "86400"  # Cache preflight for 24 hours
        
        return response
    return wrapper


@csrf_exempt
@allow_cors
@require_http_methods(["POST", "OPTIONS"])
def subscribe(request):
    """
    Public subscribe endpoint for client websites.
    
    Expects:
        - email (required): Subscriber's email address
        - name (optional): Subscriber's name (defaults to email prefix if not provided)
        - accountId (required, in header or body): Signed token identifying the newsletter owner
    
    accountIds structure: {
        "accountId1": {"active": true, "subscribed_at": "2024-01-01T00:00:00Z"},
        "accountId2": {"active": false, "subscribed_at": "2024-01-02T00:00:00Z"}
    }
    """
    # Handle preflight
    if request.method == "OPTIONS":
        return HttpResponse()
    
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"Developer": "Arun Et", "detail": "Invalid JSON"}, status=400)
        email = data.get("email")
        username = data.get("name", "")
        # Accept accountId from header or body
        accountIdFromRequest = request.headers.get("accountId") or data.get("accountId")
    else:
        email = request.POST.get("email")
        username = request.POST.get("name", "")
        accountIdFromRequest = request.headers.get("accountId") or request.POST.get("accountId")
    
    # Validate required fields
    if not email:
        return JsonResponse({"Developer": "Arun Et", "detail": "email is required"}, status=400)
    
    if not accountIdFromRequest:
        return JsonResponse({"Developer": "Arun Et", "detail": "accountId is required"}, status=400)
    
    # Validate the accountId signature
    is_valid, owner_email = validate_account_id(accountIdFromRequest)
    if not is_valid:
        return JsonResponse({"Developer": "Arun Et", "detail": "Invalid or tampered accountId"}, status=400)

    # Find the respective user id from the owner_email
    owner_user = User.objects.filter(email=owner_email).first()
    if not owner_user:
        return JsonResponse({"Developer": "Arun Et", "detail": "Invalid or deleted user account"}, status=404)
        
    accountId = owner_user.id if owner_user else None

    # Name is optional - derive from email if not provided
    name = username if username else email.split("@")[0]
    
    # Try to get an existing subscriber by email
    subscriber = Subscriber.objects.filter(email=email).first()
    now = datetime.utcnow().isoformat() + "Z"
    
    if not subscriber:
        # Create new subscriber with dict structure
        subscriber = Subscriber.objects.create(
            email=email,
            name=name,
            accountIds={accountId: {"active": True, "subscribed_at": now}}
        )
    else:
        # accountIds is now a dict: {"accountId": {"active": bool, "subscribed_at": str}}
        account_ids = subscriber.accountIds or {}
        
        # Handle migration from old list format to new dict format
        if isinstance(account_ids, list):
            account_ids = {aid: {"active": True, "subscribed_at": now} for aid in account_ids}
        
        if accountId in account_ids:
            # Check if already active
            if account_ids[accountId].get("active", True):
                return JsonResponse({
                    "Developer": "Arun Et",
                    "message": "You have already subscribed",
                    "data": {"email": email, "name": name}
                }, status=409)
            else:
                # Reactivate subscription
                account_ids[accountId]["active"] = True
                account_ids[accountId]["resubscribed_at"] = now
                subscriber.accountIds = account_ids
                subscriber.save()
                return JsonResponse({
                    "Developer": "Arun Et",
                    "message": "Subscription reactivated successfully",
                    "data": {"email": email, "name": name}
                }, status=200)
        else:
            # New subscription to this newsletter
            account_ids[accountId] = {"active": True, "subscribed_at": now}
            subscriber.accountIds = account_ids
            subscriber.save()
    
    return JsonResponse({
        "Developer": "Arun Et",
        "message": "Subscriber created successfully",
        "data": {"email": email, "name": name}
    }, status=201)


@csrf_exempt
@allow_cors
@require_http_methods(["GET", "POST", "OPTIONS"])
def unsubscribe(request):
    """
    Public unsubscribe endpoint for email links and one-click unsubscribe.
    
    Supports:
        - GET with ?token=XXX → User clicks unsubscribe link in email body
        - POST with token in body or List-Unsubscribe=One-Click → RFC 8058 one-click
    
    The token is a signed token containing subscriber_email and accountId.
    This sets the subscription to inactive (can be reactivated later).
    """
    # Handle preflight
    if request.method == "OPTIONS":
        return HttpResponse()
    
    token = None
    
    if request.method == "GET":
        # Email link click
        token = request.GET.get("token")
    elif request.method == "POST":
        # Check for RFC 8058 one-click unsubscribe
        content_type = request.content_type or ""
        
        if "application/x-www-form-urlencoded" in content_type:
            # RFC 8058: Body contains "List-Unsubscribe=One-Click"
            # Token should be in the URL query param
            token = request.GET.get("token")
            if not token:
                token = request.POST.get("token")
        elif "application/json" in content_type:
            try:
                data = json.loads(request.body.decode("utf-8"))
                token = data.get("token")
            except Exception:
                pass
        else:
            # Try query param first, then form data
            token = request.GET.get("token") or request.POST.get("token")
    
    if not token:
        return JsonResponse({
            "Developer": "Arun Et",
            "detail": "Missing unsubscribe token"
        }, status=400)
    
    # Validate the token
    is_valid, subscriber_email, account_id = validate_unsubscribe_token(token)
    if not is_valid:
        return JsonResponse({
            "Developer": "Arun Et",
            "detail": "Invalid or expired unsubscribe token"
        }, status=400)
    
    # Find the subscriber
    subscriber = Subscriber.objects.filter(email=subscriber_email).first()
    if not subscriber:
        return JsonResponse({
            "Developer": "Arun Et",
            "detail": "Subscriber not found"
        }, status=404)
    
    # Update the subscription status for this specific newsletter
    account_ids = subscriber.accountIds or {}
    
    # Handle migration from old list format
    if isinstance(account_ids, list):
        account_ids = {aid: {"active": True, "subscribed_at": ""} for aid in account_ids}
    
    if account_id not in account_ids:
        return JsonResponse({
            "Developer": "Arun Et",
            "detail": "Not subscribed to this newsletter"
        }, status=404)
    
    # Set inactive (not removing, can be reactivated)
    account_ids[account_id]["active"] = False
    account_ids[account_id]["unsubscribed_at"] = datetime.utcnow().isoformat() + "Z"
    subscriber.accountIds = account_ids
    subscriber.save()
    
    # Return HTML for browser display (email link clicks)
    if request.method == "GET" or "text/html" in request.headers.get("Accept", ""):
        html_response = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unsubscribed</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 3rem;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 400px;
        }
        .icon { font-size: 4rem; margin-bottom: 1rem; }
        h1 { color: #333; margin-bottom: 0.5rem; }
        p { color: #666; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">✅</div>
        <h1>You've been unsubscribed</h1>
        <p>You will no longer receive emails from this newsletter.</p>
        <p style="color: #999; font-size: 0.9rem;">You can resubscribe anytime by visiting the original signup page.</p>
    </div>
</body>
</html>
        """
        return HttpResponse(html_response, content_type="text/html")
    
    # Return JSON for API consumers
    return JsonResponse({
        "Developer": "Arun Et",
        "message": "Successfully unsubscribed",
        "data": {"email": subscriber_email}
    }, status=200)