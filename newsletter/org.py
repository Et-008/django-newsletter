from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Organisation
import json

def _parse_body(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}

@csrf_exempt
@require_http_methods(["POST"])
def create_org(request):
    data = _parse_body(request)
    user_id = data.get("user")
    name = data.get("name")
    if not user_id or not name:
        return JsonResponse({"Developer": "Arun Et", "message": "User and name are required to create an organisation."}, status=400)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"Developer": "Arun Et", "message": "User not found."}, status=404)

    org = Organisation.objects.create(
        name=name,
        slug=data.get("slug"),
        description=data.get("description"),
        website=data.get("website"),
        logo=data.get("logo")
    )

    # Add the user as admin of the organisation
    from .models import OrganisationMember
    OrganisationMember.objects.create(
        organisation=org,
        user=user,
        role=OrganisationMember.ROLE_ADMIN
    )

    return JsonResponse({
        "Developer": "Arun Et",
        "message": "Organisation created successfully",
        "data": org.id
    }, status=201)

@csrf_exempt
@require_http_methods(["POST"])
def update_org(request):
    data = _parse_body(request)
    org = Organisation.objects.get(id=data.get("id"))
    if not org:
        return JsonResponse({"Developer": "Arun Et", "message": "Organisation not found"}, status=404)
    org.name = data.get("name")
    if data.get("slug"):
        org.slug = data.get("slug")
    if data.get("description"):
        org.description = data.get("description")
    if data.get("website"):
        org.website = data.get("website")
    if data.get("logo"):
        org.logo = data.get("logo")
    org.save()
    return JsonResponse({"Developer": "Arun Et", "message": "Organisation updated successfully", "data": org.id}, status=200)

@csrf_exempt
@require_http_methods(["POST"])
def delete_org(request):
    data = _parse_body(request)
    org = Organisation.objects.get(id=data.get("id"))
    if not org:
        return JsonResponse({"Developer": "Arun Et", "message": "Organisation not found"}, status=404)
    org.delete()
    return JsonResponse({"Developer": "Arun Et", "message": "Organisation deleted successfully"}, status=200)

@csrf_exempt
@require_http_methods(["GET"])
def list_orgs(request):
    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"Developer": "Arun Et", "message": "user_id is required"}, status=400)
    try:
        # Filter organisations where the user is a member
        orgs = Organisation.objects.filter(members__id=user_id).distinct()
        orgs_data = []
        for org in orgs:
            orgs_data.append({
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "description": org.description,
                "website": org.website,
                "logo": org.logo.url if org.logo else None,
                "is_active": org.is_active,
                "created_at": org.created_at,
                "updated_at": org.updated_at,
            })
        return JsonResponse({
            "Developer": "Arun Et",
            "message": "Organisations listed successfully",
            "data": orgs_data
        }, status=200)
    except Exception as e:
        return JsonResponse({"Developer": "Arun Et", "message": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_org(request):
    data = _parse_body(request)
    org_id = data.get("org_id")
    if not org_id:
        return JsonResponse({"Developer": "Arun Et", "message": "Organisation ID is required"}, status=400)
    org = Organisation.objects.get(id=org_id)
    if not org:
        return JsonResponse({"Developer": "Arun Et", "message": "Organisation not found"}, status=404)
    return JsonResponse({"Developer": "Arun Et", "message": "Organisation retrieved successfully", "data": org.id}, status=200)