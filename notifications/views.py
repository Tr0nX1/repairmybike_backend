from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class IsAuthenticatedOrGuestReadOnly(permissions.BasePermission):
    """
    Allows authenticated users full access to notifications.
    Allows guest / anonymous users safe read access (returning an empty queryset)
    to prevent HTTP 403 Forbidden runtime errors on frontend clients.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        if request.method in permissions.SAFE_METHODS:
            return True
        return False

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedOrGuestReadOnly]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            # Guests do not have private notifications; safely return empty
            return Notification.objects.none()
        if user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=user)

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='mark-read', permission_classes=[permissions.IsAuthenticated])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'})

    @action(detail=False, methods=['post'], url_path='mark-all-read', permission_classes=[permissions.IsAuthenticated])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'all notifications marked as read'})
