from django.contrib import admin
from .models import Subscriber, Campaign

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "is_active", "subscribed_on")

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("subject", "sent", "created_at")
