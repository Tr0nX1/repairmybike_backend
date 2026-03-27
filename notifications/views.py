from rest_framework import status, views, permissions, generics
from rest_framework.response import Response
from .models import FCMDevice, NotificationLog, WhatsAppMessage
from .serializers import NotificationLogSerializer, WhatsAppMessageSerializer
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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

class NotificationHistoryView(generics.ListAPIView):
    """
    API endpoint to list notification history for the authenticated user.
    """
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationLog.objects.filter(user=self.request.user).order_by('-sent_at')

class WhatsAppHistoryView(generics.ListAPIView):
    """
    API endpoint to list WhatsApp message history for the authenticated user.
    """
    serializer_class = WhatsAppMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WhatsAppMessage.objects.filter(user=self.request.user).order_by('-sent_at')

class WhatsAppWebhookView(views.APIView):
    """
    Webhook for Kapso/WhatsApp status updates and incoming messages.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Verification for Webhooks
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')

        if mode == 'subscribe' and token == getattr(settings, 'KAPSO_VERIFY_TOKEN', 'repairmybike_verify_token'):
            logger.info("WhatsApp Webhook verified successfully.")
            return Response(int(challenge), status=status.HTTP_200_OK)
        return Response({'error': 'Invalid verification token'}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        # Handle status updates
        try:
            data = request.data
            # Standard WhatsApp Business API Webhook format
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    # Status updates
                    for status_update in value.get('statuses', []):
                        msg_id = status_update.get('id')
                        new_status = status_update.get('status') # sent, delivered, read, failed
                        
                        WhatsAppMessage.objects.filter(kapso_message_id=msg_id).update(status=new_status)
                        logger.info(f"WhatsApp message {msg_id} status updated to {new_status}")
            
            return Response({'status': 'ok'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
