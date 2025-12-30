from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import UploadedImage
from django.views.decorators.csrf import csrf_exempt

class ImageUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    # @ensure_csrf_cookie
    @csrf_exempt
    def post(self, request):
        file = request.FILES.get("image")
        accountId = request.headers.get("accountId")
        if accountId and file:
            img = UploadedImage.objects.create(image=file, accountId=accountId)
            return Response({
                "Developer": "Arun Et",
                "id": img.id,
                "image_url": img.image.url
            })
        else:
            return Response({
                "Developer": "Arun Et",
                "error": "Account ID and image are required"
            }, status=400)
