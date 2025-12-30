from django.urls import path

from newsletter import campaigns
from . import views
from . import auth as auth_views
from . import newsletter_apis
from . import assets
from . import config as config_views
from newsletter_project import settings
from django.conf.urls.static import static

urlpatterns = [
    path("get-csrf-token/", views.get_csrf_token, name="get_csrf_token"),
    path("subscribe/", auth_views.subscribe, name="subscribe"),
    path("update-subscriber/", auth_views.update_subscriber, name="update_subscriber"),
    path("unsubscribe/", auth_views.unsubscribe, name="unsubscribe"),
    path("send/<int:campaign_id>/", views.send_newsletter, name="send_newsletter"),
    path("html-to-image/", views.html_to_image, name="html_to_image"),
    path("fetch-html-and-convert-to-json/", newsletter_apis.fetch_html_and_convert_to_json, name="fetch_html_and_convert_to_json"),
    path("get-gemini-api/", newsletter_apis.get_gemini_api, name="get_gemini_api"),
    path("myCampaigns/", campaigns.fetch_campaigns_list, name="fetch_campaigns_list"),
    path("newsletters/", campaigns.fetch_newsletters_list, name="fetch_newsletters_list"),
    path("newsletter/create/", campaigns.create_newsletter, name="create_newsletter"),
    path("newsletter/update/", campaigns.update_newsletter, name="update_newsletter"),
    path("newsletter/delete/", campaigns.delete_newsletter, name="delete_newsletter"),
    path("newsletter/send/", campaigns.send_newsletter, name="send_newsletter"),
    path("newsletter/send-email/", newsletter_apis.send_newsletter_email, name="send_newsletter_email"),
    # Image upload endpoint
    path("assets/upload-image/", assets.ImageUploadView.as_view(), name="upload_image"),
    # Auth endpoints
    path("auth/csrf/", auth_views.csrf_token, name="auth_csrf"),
    path("auth/signup/", auth_views.signup, name="auth_signup"),
    path("auth/login/", auth_views.login_view, name="auth_login"),
    path("auth/logout/", auth_views.logout_view, name="auth_logout"),
    path("auth/me/", auth_views.me, name="auth_me"),
    path("auth/me/update/", auth_views.update_me, name="auth_update_me"),
    path("auth/change-password/", auth_views.change_password, name="auth_change_password"),
    path("auth/users/", auth_views.users_list, name="auth_users_list"),
    # Configuration endpoints
    path("config/get/", config_views.get_config, name="get_config"),
    path("config/update/", config_views.update_config, name="update_config"),
    path("config/list/", config_views.list_configs, name="list_configs"),
    path("config/create/", config_views.create_config, name="create_config"),
    path("config/<int:id>/", config_views.update_config_by_id, name="update_config_by_id"),
    path("config/<int:id>/set-primary/", config_views.set_primary, name="set_primary_config"),
    path("config/<int:id>/verify/", config_views.verify_config, name="verify_config"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)