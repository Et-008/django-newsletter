from django.shortcuts import render
import json
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Subscriber, Campaign, Item
from .serializers import ItemSerializer
from rest_framework import generics
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"message": "CSRF cookie set."}, status=200)

@require_POST
def subscribe(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        email = data.get("email")
        name = data.get("name", "")
    else:
        email = request.POST.get("email")
        name = request.POST.get("name", "")

    if not email:
        return JsonResponse({"detail": "email is required"}, status=400)

    Subscriber.objects.get_or_create(email=email, defaults={"name": name})
    return JsonResponse({"message": "Subscriber created successfully", "data": {"email": email, "name": name}}, status=201)


def send_newsletter(request, campaign_id):
    campaign = Campaign.objects.get(id=campaign_id)
    subscribers = Subscriber.objects.filter(is_active=True)

    for s in subscribers:
        send_mail(
            campaign.subject,
            "",  # plain text fallback
            settings.DEFAULT_FROM_EMAIL,
            [s.email],
            html_message=campaign.body
        )

    campaign.sent = True
    campaign.save()
    return render(request, "newsletter/success.html")

class ItemListCreate(generics.ListCreateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

class ItemRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer