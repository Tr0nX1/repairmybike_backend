from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Review, ReviewPhoto
from .serializers import ReviewSerializer, ReviewPhotoSerializer
from django.contrib.contenttypes.models import ContentType

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'upload_photo']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        review_type = self.request.query_params.get('type')
        target_id = self.request.query_params.get('target_id')
        
        if review_type:
            qs = qs.filter(review_type=review_type)
        if target_id:
            qs = qs.filter(object_id=target_id)
            
        return qs

    @action(detail=True, methods=['post'], url_path='upload-photo')
    def upload_photo(self, request, pk=None):
        review = self.get_object()
        if review.user != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
            
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
            
        photo = ReviewPhoto.objects.create(review=review, image=image)
        serializer = ReviewPhotoSerializer(photo)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
