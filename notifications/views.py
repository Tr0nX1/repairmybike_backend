from rest_framework import status, views, permissions
from rest_framework.response import Response
from .models import FCMDevice

class RegisterDeviceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        platform = request.data.get('platform')

        if not token or not platform:
            return Response(
                {'error': 'Both token and platform are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if platform not in dict(FCMDevice.PLATFORM_CHOICES):
            return Response(
                {'error': f'Invalid platform. Must be one of: {list(dict(FCMDevice.PLATFORM_CHOICES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Upsert: Update user if token exists, otherwise create
        device, created = FCMDevice.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'platform': platform,
                'is_active': True
            }
        )

        return Response(
            {
                'message': 'Device registered successfully.',
                'created': created
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

class UnregisterDeviceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        FCMDevice.objects.filter(user=request.user, token=token).update(is_active=False)
        return Response({'message': 'Device unregistered successfully.'})
