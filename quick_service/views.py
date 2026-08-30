from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from authentication.authentication import (
    GuestAuthentication,
    PasswordSessionAuthentication,
)
from authentication.permissions import IsGuestOrAuthenticated
from staff.permissions import IsStaffAuthenticated

from .models import QuickServiceConfig, QuickServiceRequest
from .serializers import (
    QuickServiceConfigSerializer,
    QuickServiceRequestCreateSerializer,
    QuickServiceRequestSerializer,
    QuickServiceRequestStaffUpdateSerializer,
)


class QuickServiceConfigView(generics.RetrieveAPIView):
    """
    GET /api/quick-service/config/
    Public endpoint: Returns singleton QuickServiceConfig object.
    Falls back to ShopInfo active phone if support_phone is blank.
    """
    serializer_class = QuickServiceConfigSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return QuickServiceConfig.get_solar_config()


class QuickServiceRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Quick Service Requests with Guest and Authenticated support.
    Endpoints:
    - POST /api/quick-service/requests/ (Create request as Guest or Authenticated User)
    - GET  /api/quick-service/requests/ (List requesting user's or guest's requests; supports ?status= and ?search=)
    - GET  /api/quick-service/requests/{id}/ (Retrieve request detail)
    - PATCH /api/quick-service/requests/{id}/ (Staff update status, notes, vehicle fields, total)
    """
    authentication_classes = [PasswordSessionAuthentication, GuestAuthentication]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if not user:
            qs = QuickServiceRequest.objects.none()
        # Staff / Superuser / Manager get all requests
        elif user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user, 'is_manager', False)):
            qs = QuickServiceRequest.objects.all().select_related('user')
        # Authenticated regular user gets their own requests
        elif user.is_authenticated:
            qs = QuickServiceRequest.objects.filter(user=user)
        # Guest user gets requests matching their X-Guest-ID
        else:
            guest_id = getattr(user, 'guest_id', None)
            if getattr(user, 'is_guest', False) and guest_id:
                qs = QuickServiceRequest.objects.filter(guest_id=guest_id)
            else:
                qs = QuickServiceRequest.objects.none()

        # Query parameter filtering: status
        status_param = self.request.query_params.get('status')
        if status_param and status_param != 'all':
            qs = qs.filter(status=status_param)

        # Query parameter filtering: search (across name, phone_number, vehicle fields)
        search_param = self.request.query_params.get('search')
        if search_param:
            qs = qs.filter(
                Q(name__icontains=search_param) |
                Q(phone_number__icontains=search_param) |
                Q(vehicle_number__icontains=search_param) |
                Q(vehicle_manufacturer__icontains=search_param) |
                Q(vehicle_model__icontains=search_param)
            )

        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return QuickServiceRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return QuickServiceRequestStaffUpdateSerializer
        return QuickServiceRequestSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsStaffAuthenticated()]
        return [IsGuestOrAuthenticated()]

    def perform_create(self, serializer):
        user = getattr(self.request, 'user', None)

        if user and user.is_authenticated:
            serializer.save(user=user, guest_id=None)
        elif user and getattr(user, 'is_guest', False) and getattr(user, 'guest_id', None):
            serializer.save(user=None, guest_id=user.guest_id)
        else:
            raise ValidationError({
                'error': True,
                'message': 'Traceability required: Either an authenticated user session or X-Guest-ID header must be provided.'
            })
