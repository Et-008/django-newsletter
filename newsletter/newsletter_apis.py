from django.shortcuts import render
import json
import re
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail, get_connection
from django.conf import settings
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from .models import UrlData
from pydantic import BaseModel, Field
from typing import List
from .models import Newsletter as NewsletterModel, EmailConfig
from .crypto_utils import decrypt_secret
# from huggingface_hub import login

from google import genai
import os

# 2. Define the JSON Schema for the Newsletter
class NewsletterSection(BaseModel):
    """A section of the newsletter."""
    heading: str = Field(description="The main heading for this section, extracted from the webpage.")
    summary: str = Field(description="A concise, engaging summary (2-3 sentences) of the content for this section.")
    key_takeaways: List[str] = Field(description="A bulleted list of 3 key facts or points from the content.")

class Newsletter(BaseModel):
    """The final structure for the JSON newsletter."""
    title: str = Field(description="A catchy, newspaper-style title for the newsletter, based on the page's main topic.")
    source_url: str
    date_generated: str
    sections: List[NewsletterSection] = Field(description="A list of content sections derived from the webpage.")

# Convert the Pydantic model to a JSON Schema string for the LLM prompt
NEWSLETTER_SCHEMA = Newsletter.model_json_schema()
# NEWSLETTER_SCHEMA = Newsletter.model_json_schema(indent=2)

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
        return JsonResponse({"data": { "source_url": url, "json_data": json.loads(url_data.json_data), "image_sources": url_data.image_sources}}, status=200)
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")

        # Clean up the HTML to remove unwanted tags and attributes
        cleaned_up_html = clean_html(soup.prettify(), clean_svg=True, clean_base64=True)
        print(cleaned_up_html, "cleaned_up_html")

        # Find all img tags and collect their src or srcset
        img_tags = soup.find_all("img")
        image_sources = []
        for img in img_tags:
            src = img.get("src")
            if src:
                image_sources.append(src)
            else:
                srcset = img.get("srcset")
                if srcset:
                    image_sources.extend([url.split()[0] for url in srcset.split(',')])
        print("Image sources found:", image_sources)

        # Convert the cleaned up HTML to Markdown
        md_content = md(cleaned_up_html, heading_style="ATX")

        final_json_output = generate_newsletter_json(md_content, NEWSLETTER_SCHEMA)
        print(final_json_output, "final_json_output")

        UrlData.objects.update_or_create(
            url=url,
            defaults={"json_data": final_json_output, "image_sources": image_sources}
        )

        return JsonResponse({"data": { "source_url": url, "json_data": json.loads(final_json_output), "image_sources": image_sources}}, status=200)
    except Exception as e:
        # You may wish to log or handle errors in production code
        raise RuntimeError(f"Error fetching or parsing HTML: {e}")



import json

# # 4. Load the Hugging Face Model (Example: Llama 3)
# model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# # Use the correct device ('cuda' if you have a powerful GPU, 'cpu' otherwise)
# device = "cuda" if torch.cuda.is_available() else "cpu"
# model = AutoModelForCausalLM.from_pretrained(model_name).to(device)


api_key = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

def generate_newsletter_json(markdown_input, schema):
    # 4a. Craft a detailed system and user prompt
    prompt = f"""
    You are an expert newsletter generator. Your task is to process the following webpage content, which is provided in Markdown format.
    
    1. Analyze the content and break it down into logical sections.
    2. For each section, generate an engaging heading, a 2-3 sentence summary, and 3 key takeaways.
    3. The final output **MUST** be a JSON object that strictly conforms to the provided JSON Schema.
    
    ### JSON Schema to follow:
    {schema}
    
    ### Webpage Content (Markdown):
    ---
    {markdown_input}
    ---
    
    Generate only the JSON object now:
    """
    
    # Use the chat template for better instruction-following
    # messages = [
    #     {"role": "user", "content": prompt}
    # ]
    
    # input_ids = tokenizer.apply_chat_template(
    #     messages,
    #     add_generation_prompt=True,
    #     return_tensors="pt"
    # ).to(device)
    
    # 4b. Generate the output
    # Key settings: max_new_tokens, temperature (low for deterministic/structured output), and forced JSON tokens
    # Note: Forcing JSON via token masks is complex. Simple instruction is often sufficient for Llama 3/Qwen.
    # output = client.models.generate_content(
    #     input_ids,
    #     max_new_tokens=2048,
    #     temperature=0.1,  # Low temperature for deterministic output
    #     do_sample=True,
    #     pad_token_id=tokenizer.eos_token_id
    # )

    output = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        },
    )

    print(output, "output")

    print(output.text, "output.text")
    
    # 4c. Decode and post-process
    # generated_text = tokenizer.decode(output[0, input_ids.shape[-1]:], skip_special_tokens=True).strip()
    generated_text = output.text
    
    # Find the start and end of the JSON block (models often wrap it in ```json ... ```)
    try:
        # json_start = generated_text.find('{')
        # json_end = generated_text.rfind('}') + 1
        # json_string = generated_text[json_start:json_end].strip()
        
        # # 4d. Validate the output against the Pydantic model
        # json_data = json.loads(json_string)
        # validated_newsletter = Newsletter(**json_data)
        
        # return validated_newsletter.json(indent=2)

        return generated_text
    
    except (json.JSONDecodeError, ValueError, AttributeError):
        print("Error: Failed to extract or validate JSON from LLM output.")
        print("Raw LLM Output:\n", generated_text)
        return None

# # # Final Call:
# # final_json_output = generate_newsletter_json(cleaned_markdown_text, NEWSLETTER_SCHEMA, model, tokenizer)
# # print(final_json_output)

@csrf_exempt
def get_gemini_api(request):
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return JsonResponse({"detail": "GEMINI_API_KEY not set"}, status=500)
    print(api_key, "api_key")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=request.GET.get('ques', '')
    )
    return JsonResponse({"text": response.text}, status=200)


@require_POST
@csrf_exempt
def send_newsletter_email(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)

        title = data.get("title")
        html = data.get("html")
        subscribers = data.get("subscribers")
        newsletter_id = data.get("newsletter_id")
        email_config_id = data.get("email_config_id")

        if title and html and len(subscribers) > 0:
            # Resolve user-specific email backend if available
            connection = None
            from_email = settings.DEFAULT_FROM_EMAIL
            try:
                if request.user and request.user.is_authenticated:
                    if email_config_id:
                        config = EmailConfig.objects.get(id=email_config_id)
                    else:
                        config = EmailConfig.objects.filter(user=request.user, is_active=True).order_by("-is_primary", "-updated_at").first()
                    if config:
                        password = decrypt_secret(config.password_encrypted) if config.password_encrypted else ""
                        connection = get_connection(
                            backend="django.core.mail.backends.smtp.EmailBackend",
                            host=config.host,
                            port=config.port,
                            username=config.username,
                            password=password,
                            use_tls=config.use_tls,
                            use_ssl=config.use_ssl,
                            timeout=10,
                        )
                        from_email = config.from_email or from_email
            except Exception:
                connection = None  # fallback to default

            if not connection:
                return JsonResponse({"Developer": "Arun Et", "message": "Failed to establish connection"}, status=500)

            for s in subscribers:
                print(s['email'], "s.email")
                send_mail(
                    title,
                    "",  # plain text fallback
                    from_email,
                    [s['email']],
                    html_message=html,
                    connection=connection,
                )

            # This line: Newsletter.objects.filter(id=newsletter_id).update(sent=True)
            # could throw an error if:
            # - Newsletter is not imported or defined at the top of the file
            # - newsletter_id is None or not the correct type (e.g., not an int or str as expected)
            # - There is no Newsletter model defined in your models.py
            # - The database connection fails, or the migrations weren't applied
            # There are no code changes per instructions.
            NewsletterModel.objects.filter(id=newsletter_id).update(sent=True)
            return JsonResponse({"Developer": "Arun Et", "message": "Newsletter sent successfully"}, status=200)