import os
from django.shortcuts import render
import json
import re
import ollama
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Subscriber, Campaign
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
from .models import UrlData

# from transformers import AutoModelForCausalLM, AutoTokenizer

# device = "cpu"  # or "cpu"
# tokenizer = AutoTokenizer.from_pretrained("jinaai/ReaderLM-v2")
# model = AutoModelForCausalLM.from_pretrained("jinaai/ReaderLM-v2").to(device)


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

@csrf_exempt
@require_POST
def html_to_image(request):
    # Get URL from POST data (json or form)
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
    if UrlData.objects.filter(url=url).exists():
        print(UrlData.objects.get(url=url), "UrlData.objects.get")
        url_data = UrlData.objects.get(url=url)
        if url_data.image and os.path.exists(url_data.image.path):
            return JsonResponse({"image_url": f"/media/url_images/{cleaned_url}.png"})
            # return HttpResponse(open(url_data.image.path, "rb").read(), content_type="image/png")

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            request_data = json.loads(request.body.decode("utf-8"))
            page.goto(request_data.get("url") or request.POST.get("url"))
            page.screenshot(path=f"/media/url_images/{cleaned_url}.png", full_page=False)
            browser.close()
    except Exception as e:
        return JsonResponse({"detail": f"Failed to convert HTML to image: {e}"}, status=500)

    # Save image and url mapping using UrlData model
    try:
        # Make sure the file path matches where you saved the screenshot

        with open(f"/media/url_images/{cleaned_url}.png", "rb") as img_file:
            # Remove old UrlData for this URL if exists (optional: not required unless you want single record per url)
            # UrlData.objects.filter(url=url).delete()

            url_data, created = UrlData.objects.update_or_create(url=url)
            url_data.image.save(f"/media/url_images/{cleaned_url}.png", img_file, save=True)
            url_data.save()
    except Exception as save_exc:
        # Ignore db errors, but in production you might want to log this
        pass
    return JsonResponse({"image_url": f"/media/url_images/{cleaned_url}.png"})


@csrf_exempt
@require_POST
def fetch_html_and_convert_to_json(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        url = data.get("url")
    else:
        url = request.POST.get("url")
    if not url:
        return JsonResponse({"detail": "url is required"}, status=400)
    if UrlData.objects.filter(url=url).exists() and UrlData.objects.get(url=url).json_data != "":
        url_data = UrlData.objects.get(url=url)
        return JsonResponse({"data": json.loads(url_data.json_data)}, status=200)
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Clean up the HTML to remove unwanted tags and attributes
        cleaned_up_html = clean_html(soup.prettify(), clean_svg=True, clean_base64=True)

        # Convert the cleaned up HTML to Markdown
        md_content = md(cleaned_up_html, heading_style="ATX")
        print(md_content, "md_content")

        # Log the raw soup variable (HTML) to a file as a new entry per request
        # try:
        #     # If "html_request_log.txt" does not exist, opening it with mode "a" will create it automatically.
        #     with open("html_request_log.txt", "a", encoding="utf-8") as log_file:
        #         log_file.write("==== New Request ====\n")
        #         log_file.write(soup.prettify())
        #         log_file.write("\n\n")
        # except Exception as log_exc:
        #     # Don't interrupt regular flow, but you might want to log this in production
        #     pass

        # # Example: Extracting title and main content
        # title = soup.find('h1').get_text(strip=True) if soup.find('h1') else 'No Title Found'
        
        # # Assuming main content is within a specific div or article tag
        # content_divs = soup.find_all('div', class_='ck-content') or soup.find_all('article')
        
        # paragraphs = []

        # if content_divs:
        #     for content_div in content_divs:
        #         for p_tag in content_div.find_all('p'):
        #             paragraphs.append(p_tag.get_text(strip=True))

        json_data = generate_json_from_html_with_llama(md_content)
        print(json_data, "json_data")

        # Ensure json_data can be stored as text (serialize to JSON string if needed)
        # if json_data is not None:
        #     json_data_str = json.dumps(json_data) if not isinstance(json_data, str) else json_data
        # else:
        #     json_data_str = ""

        url_data_obj, created = UrlData.objects.update_or_create(
            url=url,
            defaults={"json_data": json_data}
        )

        return JsonResponse({"data": json_data}, status=200)
    except Exception as e:
        # You may wish to log or handle errors in production code
        raise RuntimeError(f"Error fetching or parsing HTML: {e}")


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

@csrf_exempt
@require_POST
def generate_newsletter_body(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)
        url = data.get("url")
    else:
        url = request.POST.get("url")
    if not url:
        return JsonResponse({"detail": "url is required"}, status=400)
    try:
        blog_data = fetch_html_and_convert_to_json(url)
        newsletter_body = f"<h1>{blog_data['title']}</h1> <br><br> {blog_data['content']}"
        return JsonResponse({"data": newsletter_body}, status=200)
    except Exception as e:
        return JsonResponse({"detail": f"Failed to generate newsletter body: {e}"}, status=500)

def create_prompt(
    text: str, tokenizer=None, instruction: str = None, schema: str = None
) -> str:
    """
    Create a prompt for the model with optional instruction and JSON schema.
    """
    if not instruction:
        instruction = "Extract the main content from the given HTML and convert it to Markdown format."
    if schema:
        instruction = "Extract the specified information from a list of news threads and present it in a structured JSON format."
        prompt = f"{instruction}\n```html\n{text}\n```\nThe JSON schema is as follows:```json\n{schema}\n```"
    else:
        prompt = f"{instruction}\n```html\n{text}\n```"

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def generate_json_from_html_with_llama(clean_text):

    ollama.pull("milkey/reader-lm-v2:latest")

    schema = """
    {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "The subject line of the newsletter email"
            },
            "preheader": {
                "type": "string",
                "description": "The preheader text that summarizes the newsletter"
            },
            "header_image_url": {
                "type": "string",
                "description": "URL to the header image used in the newsletter, if any"
            },
            "sections": {
                "type": "array",
                "description": "A list of sections in the newsletter",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content_html": {"type": "string"},
                        "cta_label": {"type": "string"},
                        "cta_url": {"type": "string"}
                    },
                    "required": ["title", "content_html"]
                }
            },
            "footer_html": {
                "type": "string",
                "description": "HTML content for the newsletter footer, including unsubscribe and contact info"
            }
        },
        "required": ["subject", "preheader", "sections", "footer_html"]
    }
    """

    # # Send a chat request with the milkey/reader-lm-v2:latest model
    llm_response = ollama.chat(
        model="milkey/reader-lm-v2:latest",
        # format="json",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant for extracting and summarizing information from Markdown."
            },
            {
                "role": "user",
                "content": f"Extract data from the following Markdown and convert it to a structured HTML format \n\n md_content: {clean_text}"
            }
        ],
    )

    print(llm_response, "llm_response")

    # response = json.loads(llm_response['message']['content'])   # type: ignore

    # print(response, "response")

    return llm_response['message']['content']

    # html = clean_html(clean_text)
    # input_prompt = create_prompt(html, tokenizer=tokenizer, schema=schema)

    # inputs = tokenizer.encode(input_prompt, return_tensors="pt").to(device)
    # outputs = model.generate(
    #     inputs, max_new_tokens=1024, temperature=0, do_sample=False, repetition_penalty=1.08
    # )

    # print(tokenizer.decode(outputs[0]))

    # response = ollama.generate(
    #     model="reader-lm:1.5b",
    #     prompt=f"{PROMPT}nn{clean_text}",
    #     stream=False,
    #     format="json",
    #     options={"temperature": 0.1, "num_ctx": 12000},
    # )

    # print(response)

    # return response
    # raw_output = response.json()["response"].strip()
    # product_data = json.loads(raw_output)
    # return product_data


# Patterns
SCRIPT_PATTERN = r"<[ ]*script.*?\/[ ]*script[ ]*>"
STYLE_PATTERN = r"<[ ]*style.*?\/[ ]*style[ ]*>"
META_PATTERN = r"<[ ]*meta.*?>"
COMMENT_PATTERN = r"<[ ]*!--.*?--[ ]*>"
LINK_PATTERN = r"<[ ]*link.*?>"
BASE64_IMG_PATTERN = r'<img[^>]+src="data:image/[^;]+;base64,[^"]+"[^>]*>'
SVG_PATTERN = r"(<svg[^>]*>)(.*?)(<\/svg>)"


def replace_svg(html: str, new_content: str = "this is a placeholder") -> str:
    return re.sub(
        SVG_PATTERN,
        lambda match: f"{match.group(1)}{new_content}{match.group(3)}",
        html,
        flags=re.DOTALL,
    )


def replace_base64_images(html: str, new_image_src: str = "#") -> str:
    return re.sub(BASE64_IMG_PATTERN, f'<img src="{new_image_src}"/>', html)


def clean_html(html: str, clean_svg: bool = False, clean_base64: bool = False):
    html = re.sub(
        SCRIPT_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        STYLE_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        META_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        COMMENT_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    html = re.sub(
        LINK_PATTERN, "", html, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    if clean_svg:
        html = replace_svg(html)
    if clean_base64:
        html = replace_base64_images(html)
    return html
