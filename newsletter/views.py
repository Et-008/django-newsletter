from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from .models import Subscriber, Campaign

def subscribe(request):
    if request.method == "POST":
        email = request.POST.get("email")
        name = request.POST.get("name", "")
        Subscriber.objects.get_or_create(email=email, defaults={"name": name})
        return render(request, "newsletter/success.html")
    return render(request, "newsletter/subscribe.html")


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
