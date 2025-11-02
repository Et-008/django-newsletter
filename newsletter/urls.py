from django.urls import path
from . import views

urlpatterns = [
    path("get-csrf-token/", views.get_csrf_token, name="get_csrf_token"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("send/<int:campaign_id>/", views.send_newsletter, name="send_newsletter"),
    path("items/", views.ItemListCreate.as_view(), name="item-list-create"),
    path("items/<int:pk>/", views.ItemRetrieveUpdateDestroy.as_view(), name="item-retrieve-update-destroy"),
]
