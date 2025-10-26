from django.urls import path
from . import views

urlpatterns = [
    path("subscribe/", views.subscribe, name="subscribe"),
    path("send/<int:campaign_id>/", views.send_newsletter, name="send_newsletter"),
]
