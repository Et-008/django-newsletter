import os
from django.shortcuts import render
import json
import re
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Subscriber, Campaign
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import UrlData
from pathlib import Path
import environ
import requests
from requests.auth import HTTPBasicAuth

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))

# Reads .env locally, ignored in Render
environ.Env.read_env(BASE_DIR / ".env")


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"message": "CSRF cookie set."}, status=200)

@csrf_exempt
@require_POST
def html_to_image(request):
    # Get URL from POST data (json or form)
    from playwright.sync_api import sync_playwright
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        url = data.get("url")

        cleaned_url = re.sub(r'[/.]', '_', re.sub(r'^https?://', '', url))
    else:
        url = request.POST.get("url")
    if not url:
        return JsonResponse({"detail": "url is required"}, status=400)
    if env("DEBUG") == True:
        if UrlData.objects.filter(url=url).exists():
            # print(UrlData.objects.get(url=url), "UrlData.objects.get")
            url_data = UrlData.objects.get(url=url)
            if url_data.image and os.path.exists(url_data.image.path):
                return JsonResponse({"image_url": f"http://localhost:8000/api/media/url_images/{cleaned_url}.png"})
                # return HttpResponse(open(url_data.image.path, "rb").read(), content_type="image/png")
    else:
        # If debug is false, upload the image to imagekit
        from imagekitio import ImageKit

        imagekit = ImageKit(
            private_key=env("IMAGEKIT_PRIVATE_KEY"),
            # url_endpoint=env("IMAGEKIT_URL_ENDPOINT")
            base_url="https://api.imagekit.io/v1/files"
        )

        response = requests.get(
            "https://api.imagekit.io/v1/files",
            params={
                "path": f"/url_images/{cleaned_url}",
                "limit": 100,
            },
            auth=HTTPBasicAuth(env("IMAGEKIT_PRIVATE_KEY"), ""),
        )

        response.raise_for_status()
        files = response.json()
        
        if files and len(files) > 0:
            return JsonResponse({"image_url": files[0]["url"]})

    try:
        # Ensure the url_images directory exists
        url_images_dir = os.path.join(settings.MEDIA_ROOT, "url_images")
        os.makedirs(url_images_dir, exist_ok=True)
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                    "--no-zygote",
                    "--single-process",
                ]
            )
            page = browser.new_page()
            request_data = json.loads(request.body.decode("utf-8"))
            page.goto(request_data.get("url") or request.POST.get("url"))
            if env("DEBUG") == True:
                page.screenshot(path=os.path.join(url_images_dir, f"{cleaned_url}.png"), full_page=False)
            else:
                image_bytes = page.screenshot(full_page=False)
            browser.close()
    except Exception as e:
        return JsonResponse({"detail": f"Failed to convert HTML to image: {e}"}, status=500)

    # Save image and url mapping using UrlData model
    if env("DEBUG") == True:
        try:
            # Make sure the file path matches where you saved the screenshot
            # If debug is true, save the image to the media root
            with open(os.path.join(settings.MEDIA_ROOT, "url_images", f"{cleaned_url}.png"), "rb") as img_file:
                # Remove old UrlData for this URL if exists (optional: not required unless you want single record per url)
                # UrlData.objects.filter(url=url).delete()

                url_data, created = UrlData.objects.update_or_create(url=url)
                url_data.image.save(f"{cleaned_url}.png", img_file, save=True)
                url_data.save()
        except Exception as save_exc:
            # Ignore db errors, but in production you might want to log this
            return JsonResponse({"detail": f"Failed to save/upload image: {save_exc}"}, status=500)
        
        return JsonResponse({"image_url": f"http://localhost:8000/api/media/url_images/{cleaned_url}.png"})
    else:
        try:
            result = imagekit.files.upload(
                file=image_bytes,
                file_name=f"webpage_screenshot.png",
                folder=f"/url_images/{cleaned_url}",
                use_unique_file_name=False,
            )

            # print(result.url, "result.url")
            image_url = None

            if result and result.url:
                image_url = result.url
        except Exception as save_exc:
            # Ignore db errors, but in production you might want to log this
            return JsonResponse({"detail": f"Failed to save/upload image: {save_exc}"}, status=500)
        
        if image_url is None:
            return JsonResponse({"detail": "Failed to generate image URL"}, status=500)
        
        return JsonResponse({"image_url": image_url})


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
