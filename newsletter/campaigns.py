from django.views.decorators.csrf import ensure_csrf_cookie
from .models import  Campaign, Newsletter
from django.http import  JsonResponse
from django.views.decorators.csrf import csrf_exempt
from markdownify import markdownify as md
from .auth import _parse_body
from datetime import datetime

dummmyResponse = {
    "newsLetterSections": [
        {
            "id": "98f7befb-d415-4cf0-b3fa-d898c9ec441e",
            "type": "heading",
            "text": "Global Reach: Mastering Localization Quality Assurance",
            "level": 1,
            "h1": {
            "fontSize": 32,
            "fontWeight": 700
            },
            "h2": {
            "fontSize": 24,
            "fontWeight": 600
            },
            "h3": {
            "fontSize": 18,
            "fontWeight": 600
            },
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "fontSize": 24,
            "fontWeight": 600
        },
        {
            "id": "030df802-809d-467c-96d1-801ab3e28080",
            "type": "image",
            "src": "https://lang-q.com/_next/image?url=%2Fimages%2Fquality-check.jpeg&w=3840&q=75",
            "alt": "Image",
            "width": "100%",
            "height": "auto",
            "alignment": "center",
            "borderRadius": 0
        },
        {
            "id": "b05b6e51-7bd0-480d-adb0-e1d147b1e9d0",
            "type": "heading",
            "text": "Why Localization Quality Assurance (LQA) is Essential",
            "level": 3,
            "h1": {
            "fontSize": 32,
            "fontWeight": 700
            },
            "h2": {
            "fontSize": 24,
            "fontWeight": 600
            },
            "h3": {
            "fontSize": 18,
            "fontWeight": 600
            },
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "fontSize": 16,
            "fontWeight": 600
        },
        {
            "id": "78e9ab46-9215-4a5c-b253-45e28cc3d23c",
            "type": "paragraph",
            "content": "<p>Poor localization leads to bad user experience, brand erosion, and potential legal issues.</p>",
            "fontSize": 16,
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "lineHeight": 1.6,
            "backgroundColor": "transparent"
        },
        {
            "id": "ba7d208d-403b-43f9-a1ec-8dadca5de512",
            "type": "heading",
            "text": "LQA: Terminology Breakdown",
            "level": 2,
            "h1": {
            "fontSize": 32,
            "fontWeight": 700
            },
            "h2": {
            "fontSize": 24,
            "fontWeight": 600
            },
            "h3": {
            "fontSize": 18,
            "fontWeight": 600
            },
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "fontSize": 24,
            "fontWeight": 600
        },
        {
            "id": "2694f89d-9f63-497e-8e03-88d09a544a3f",
            "type": "paragraph",
            "content": "<p>Linguistic Testing verifies language functionality in its environment.</p>",
            "fontSize": 16,
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "lineHeight": 1.6,
            "backgroundColor": "transparent"
        },
        {
            "id": "820748d0-d02d-40a7-8e8c-1581f4c1086f",
            "type": "heading",
            "text": "Step 1: Pre-Planning and Setup for High-Quality LQA",
            "level": 2,
            "h1": {
            "fontSize": 32,
            "fontWeight": 700
            },
            "h2": {
            "fontSize": 24,
            "fontWeight": 600
            },
            "h3": {
            "fontSize": 18,
            "fontWeight": 600
            },
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "fontSize": 24,
            "fontWeight": 600
        },
        {
            "id": "ad2915e2-61f5-43bd-a983-a13f29fd1aa0",
            "type": "paragraph",
            "content": "<p>Define clear quality standards and create reference tools like style guides and glossaries.</p>",
            "fontSize": 16,
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "lineHeight": 1.6,
            "backgroundColor": "transparent"
        },
        {
            "id": "b2e95ae5-28e2-4e94-9583-4dd5f27bc22e",
            "type": "heading",
            "text": "The Verdict: LQA's Worthwhile Investment",
            "level": 2,
            "h1": {
            "fontSize": 32,
            "fontWeight": 700
            },
            "h2": {
            "fontSize": 24,
            "fontWeight": 600
            },
            "h3": {
            "fontSize": 18,
            "fontWeight": 600
            },
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "fontSize": 24,
            "fontWeight": 600
        },
        {
            "id": "c59f65e8-7239-4695-af5c-aad4afb7865e",
            "type": "paragraph",
            "content": "<p>Investing in LQA contributes to a strong localization ROI and global market success.</p>",
            "fontSize": 16,
            "fontFamily": "Arial, sans-serif",
            "color": "#333333",
            "alignment": "left",
            "lineHeight": 1.6,
            "backgroundColor": "transparent"
        },
        {
            "id": "c876b037-d7d5-42a9-ad9d-33309eb269bd",
            "type": "button",
            "text": "Read full article",
            "href": "https://lang-q.com/blog/how-to-check-the-quality-of-localized-content",
            "backgroundColor": "#007bff",
            "textColor": "#ffffff",
            "borderRadius": 4,
            "padding": "12px 24px",
            "fontSize": 16,
            "alignment": "center",
            "width": "auto"
        },
        {
            "id": "440a7b13-bb56-48c3-97de-99352f1884de",
            "type": "socialLinks",
            "platforms": [
            {
                "type": "youtube",
                "url": "#"
            },
            {
                "type": "linkedin",
                "url": "#"
            },
            {
                "type": "instagram",
                "url": "#"
            },
            {
                "type": "twitter",
                "url": "#"
            }
            ],
            "iconSize": 32,
            "spacing": 12,
            "alignment": "center",
            "iconStyle": "circular"
        }
    ] 
}

@ensure_csrf_cookie
# @csrf_exempt
def fetch_campaigns_list(request):
    # Check for campaign_id in query params if not already in body
    if request.GET.get("campaign_id"):
        campaign_id = request.GET.get("campaign_id")
        accountId = request.headers.get("accountId")
        if campaign_id:
            if accountId:
                campaigns = Campaign.objects.filter(id=campaign_id, accountId=accountId).values("id", "subject", "created_at", "body", "sent")
            else:
                campaigns = Campaign.objects.filter(id=campaign_id).values("id", "subject", "created_at", "body", "sent")
            campaigns_list = list(campaigns)
        return JsonResponse({"Developer": "Arun Et", "campaign": campaigns_list[0], "newsLetterSections": dummmyResponse["newsLetterSections"]})
    else:
        accountId = request.headers.get("accountId")
        if accountId:
            campaigns = Campaign.objects.filter(accountId=accountId).values("id", "subject", "created_at", "body", "sent")
        else:
            campaigns = Campaign.objects.all().values("id", "subject", "created_at", "body", "sent")
        campaigns_list = list(campaigns)
        return JsonResponse({"Developer": "Arun Et", "campaigns": campaigns_list})

@ensure_csrf_cookie
def fetch_newsletters_list(request):
    if request.GET.get("newsletter_id"):
        newsletter_id = request.GET.get("newsletter_id")
        accountId = request.headers.get("accountId")
        if newsletter_id:
            if accountId:
                newsletter = Newsletter.objects.filter(id=newsletter_id, accountId=accountId).values("id", "title", "source_url", "date_generated", "sent", "sections")
            else:
                newsletter = Newsletter.objects.filter(id=newsletter_id).values("id", "title", "source_url", "date_generated", "sent", "sections")
        newsletters_list = list(newsletter)
    else:
        accountId = request.headers.get("accountId")
        if accountId:
            newsletters = Newsletter.objects.filter(accountId=accountId).values("id", "title", "source_url", "date_generated", "sent", "sections")
        else:
            newsletters = Newsletter.objects.all().values("id", "title", "source_url", "date_generated", "sent", "sections")
        newsletters_list = list(newsletters)
    return JsonResponse({"Developer": "Arun Et", "newsletters": newsletters_list})

# @ensure_csrf_cookie
@csrf_exempt
def create_newsletter(request):
    if request.method == "POST":
        data = _parse_body(request)
        title = data.get("title")
        sections = data.get("sections")
        html_content = data.get("html_content")
        accountId = request.headers.get("accountId")
        if accountId and title and sections and html_content:
            newsletter = Newsletter.objects.create(title=title, sections=sections, html_content=html_content, sent=False, accountId=accountId, date_generated=datetime.now())
            return JsonResponse({"Developer": "Arun Et", "newsletter": newsletter.id})
        else:
            return JsonResponse({"Developer": "Arun Et", "error": "Account ID, title, sections, and html_content are required"}, status=400)


# @ensure_csrf_cookie
@csrf_exempt
def update_newsletter(request):
    if request.method == "POST":
        data = _parse_body(request)
        newsletter_id = data.get("newsletter_id")
        title = data.get("title")
        sections = data.get("sections")
        html_content = data.get("html_content")
        accountId = request.headers.get("accountId")
        if accountId and newsletter_id and title and sections and html_content:
            Newsletter.objects.filter(id=newsletter_id, accountId=accountId).update(title=title, sections=sections, html_content=html_content)
            return JsonResponse({"Developer": "Arun Et", "message": "Newsletter updated successfully"}, status=200)
        else:
            return JsonResponse({"Developer": "Arun Et", "error": "Account ID, newsletter ID, title, sections, and html_content are required"}, status=400)


# @ensure_csrf_cookie
@csrf_exempt
def delete_newsletter(request):
    if request.method == "POST":
        data = _parse_body(request)
        newsletter_id = data.get("newsletter_id")
        accountId = request.headers.get("accountId")
        if accountId and newsletter_id:
            Newsletter.objects.filter(id=newsletter_id, accountId=accountId).delete()
            return JsonResponse({"Developer": "Arun Et", "message": "Newsletter deleted successfully"}, status=200)
        else:
            return JsonResponse({"Developer": "Arun Et", "error": "Account ID and newsletter ID are required"}, status=400)


# @ensure_csrf_cookie
@csrf_exempt
def send_newsletter(request):
    if request.method == "POST":
        data = _parse_body(request)
        newsletter_id = data.get("newsletter_id")
        accountId = request.headers.get("accountId")
        if accountId and newsletter_id:
            Newsletter.objects.filter(id=newsletter_id, accountId=accountId).update(sent=True)
            return JsonResponse({"Developer": "Arun Et", "message": "Newsletter sent successfully"}, status=200)
        else:
            return JsonResponse({"Developer": "Arun Et", "error": "Account ID and newsletter ID are required"}, status=400)