from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from bookings.models import Booking, BookingPart, BookingService
from services.models import Service, ServicePricing
from spare_parts.models import SparePart
from bookings.serializers import BookingDetailSerializer, BookingPartSerializer
from rest_framework import permissions
from .permissions import IsStaffAuthenticated, IsSuperUser, IsSuperuserOrManager
from .models import ActivityLog, CashMovement, CashReconciliation, CashSession
from .serializers import (
    ActivityLogSerializer,
    CashMovementSerializer,
    CashReconciliationSerializer,
    CashSessionSerializer,
    StaffUserSerializer,
)
from authentication.serializers import AdminUserSerializer

User = get_user_model()


class StaffUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Staff user list for mechanic assignment dropdowns.
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffAuthenticated]
    serializer_class = StaffUserSerializer

    def get_queryset(self):
        return User.objects.filter(is_staff=True, is_active=True).order_by('first_name', 'last_name', 'username')

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({
            'error': False,
            'message': 'Staff list retrieved successfully',
            'data': serializer.data,
        })


class UserManagementViewSet(viewsets.GenericViewSet):
    """
    User management for administrators and managers.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperuserOrManager]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().order_by('-created_at')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search', '').strip()
        role_filter = self.request.query_params.get('role', '').lower()
        is_staff = self.request.query_params.get('is_staff')
        is_active = self.request.query_params.get('is_active')

        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(phone_number__icontains=search)
            )

        if role_filter == 'staff':
            qs = qs.filter(is_staff=True, is_superuser=False)
        elif role_filter == 'manager':
            qs = qs.filter(is_manager=True, is_superuser=False)
        elif role_filter == 'superuser':
            qs = qs.filter(is_superuser=True)

        if is_staff is not None:
            if str(is_staff).lower() in ['true', '1', 'yes']:
                qs = qs.filter(is_staff=True)
            elif str(is_staff).lower() in ['false', '0', 'no']:
                qs = qs.filter(is_staff=False)

        if is_active is not None:
            if str(is_active).lower() in ['true', '1', 'yes']:
                qs = qs.filter(is_active=True)
            elif str(is_active).lower() in ['false', '0', 'no']:
                qs = qs.filter(is_active=False)

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'User list retrieved successfully',
            'data': serializer.data,
        })

    @action(detail=True, methods=['patch'], url_path='roles')
    def roles(self, request, pk=None):
        user = request.user
        target_user = self.get_object()
        if not (user.is_superuser or getattr(user, 'is_manager', False)):
            return Response({
                'error': 'Manager or superuser privileges required'
            }, status=status.HTTP_403_FORBIDDEN)

        payload = request.data
        changes = {}

        if 'is_staff' in payload or 'is_superuser' in payload:
            if not user.is_superuser:
                return Response({
                    'error': 'Only superusers can change staff or superuser roles',
                    'code': 'SUPERUSER_REQUIRED'
                }, status=status.HTTP_403_FORBIDDEN)

        if user.id == target_user.id and 'is_superuser' in payload and str(payload.get('is_superuser')).lower() in ['false', '0', 'no']:
            return Response({
                'error': 'You cannot remove your own superuser access',
                'code': 'SELF_DEMOTION'
            }, status=status.HTTP_403_FORBIDDEN)

        def parse_bool(value):
            if isinstance(value, bool):
                return value
            return str(value).lower() in ['true', '1', 'yes']

        for field in ['is_active', 'is_staff', 'is_superuser', 'is_manager']:
            if field in payload:
                new_value = parse_bool(payload.get(field))
                setattr(target_user, field, new_value)
                changes[field] = new_value

        if changes:
            target_user.save(update_fields=list(changes.keys()))
            ActivityLog.objects.create(
                user=user,
                action_type='user_role_changed',
                description=f"Updated roles for {target_user.username}",
                content_object=target_user,
                metadata={
                    'target_user': str(target_user.id),
                    'changes': changes,
                }
            )

        serializer = self.get_serializer(target_user)
        return Response({
            'error': False,
            'message': 'User roles updated successfully',
            'data': serializer.data,
        })


class ActivityLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


def calculate_cash_session_totals(session):
    totals = session.movements.values('movement_type').annotate(total=Sum('amount'))
    movement_totals = {
        item['movement_type']: item['total'] or Decimal('0.00')
        for item in totals
    }
    total_collections = movement_totals.get(CashMovement.TYPE_COLLECTION, Decimal('0.00'))
    total_expenses = movement_totals.get(CashMovement.TYPE_EXPENSE, Decimal('0.00'))
    total_adjustments = movement_totals.get(CashMovement.TYPE_ADJUSTMENT, Decimal('0.00'))
    calculated_closing = session.opening_balance + total_collections + total_adjustments - total_expenses

    return {
        'total_collections': total_collections,
        'total_expenses': total_expenses,
        'total_adjustments': total_adjustments,
        'calculated_closing': calculated_closing,
    }


def close_cash_session(request, session, actual_closing, notes=None):
    totals = calculate_cash_session_totals(session)
    reconciliation_serializer = CashReconciliationSerializer(
        data={
            'session': session.id,
            'total_collections': totals['total_collections'],
            'total_expenses': totals['total_expenses'],
            'total_adjustments': totals['total_adjustments'],
            'calculated_closing': totals['calculated_closing'],
            'actual_closing': actual_closing,
        },
        context={'request': request}
    )
    reconciliation_serializer.is_valid(raise_exception=True)
    reconciliation = reconciliation_serializer.save()

    session.closing_balance = actual_closing
    session.expected_closing = totals['calculated_closing']
    session.variance = reconciliation.variance
    session.status = (
        CashSession.STATUS_PENDING_APPROVAL
        if abs(reconciliation.variance) > Decimal('100.00')
        else CashSession.STATUS_APPROVED
    )
    if notes is not None:
        session.notes = notes
    session.save()

    ActivityLog.objects.create(
        user=request.user,
        action_type='cash_session_closed',
        description=f"Cash session #{session.id} closed with variance {session.variance}",
        content_object=session,
        metadata={
            'old_value': CashSession.STATUS_OPEN,
            'new_value': session.status,
            'amount': str(actual_closing),
            'actual_closing': str(actual_closing),
            'expected_closing': str(session.expected_closing),
            'variance': str(session.variance),
            'status': session.status,
            'reconciliation_id': reconciliation.id,
            'session_id': session.id,
        }
    )
    return reconciliation


class CashSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Staff cash session endpoints for daily cash reconciliation.
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffAuthenticated]
    queryset = CashSession.objects.select_related('staff', 'approved_by').prefetch_related('movements').all()
    serializer_class = CashSessionSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        
        # Managers and Admins see all with filters
        if user.is_superuser or getattr(user, 'is_manager', False):
            staff_id = self.request.query_params.get('staff_id')
            date_from = self.request.query_params.get('date_from')
            date_to = self.request.query_params.get('date_to')
            status_filter = self.request.query_params.get('status')
            
            if staff_id:
                qs = qs.filter(staff_id=staff_id)
            if date_from:
                qs = qs.filter(date__gte=date_from)
            if date_to:
                qs = qs.filter(date__lte=date_to)
            if status_filter:
                qs = qs.filter(status=status_filter)
            return qs
            
        # Regular staff only see their own sessions
        return qs.filter(staff=user)

    @action(detail=True, methods=['get'], url_path='movements')
    def movements(self, request, pk=None):
        session = self.get_object()
        movements = session.movements.all().select_related('booking', 'booking__customer', 'recorded_by')
        from .serializers import CashMovementSerializer
        return Response({
            'error': False,
            'data': CashMovementSerializer(movements, many=True).data
        })

    @action(detail=True, methods=['post'], url_path='approve')
    @transaction.atomic
    def approve(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, 'is_manager', False)):
            return Response({'error': 'Manager privileges required'}, status=status.HTTP_403_FORBIDDEN)
            
        session = CashSession.objects.select_for_update().get(pk=self.get_object().pk)
        approved = request.data.get('approved', True)
        notes = request.data.get('notes', '')
        
        if session.status != CashSession.STATUS_PENDING_APPROVAL:
            return Response({'error': 'Only sessions pending approval can be approved/flagged'}, status=status.HTTP_400_BAD_REQUEST)
            
        session.status = CashSession.STATUS_APPROVED if approved else CashSession.STATUS_FLAGGED
        session.approved_by = request.user
        session.approved_at = timezone.now()
        if notes:
            session.approval_notes = notes
        session.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action_type='cash_session_approved' if approved else 'cash_session_flagged',
            description=f"Cash session #{session.id} {'approved' if approved else 'flagged'}",
            content_object=session,
            metadata={
                'old_value': CashSession.STATUS_PENDING_APPROVAL,
                'new_value': session.status,
                'notes': notes
            }
        )
        
        return Response({
            'error': False,
            'message': f"Cash session {'approved' if approved else 'flagged'} successfully",
            'data': self.get_serializer(session).data
        })

    @action(detail=False, methods=['post'], url_path='start')
    @transaction.atomic
    def start(self, request):
        opening_balance = request.data.get('opening_balance')
        if opening_balance is None:
            return Response({
                'error': True,
                'message': 'opening_balance field is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.localdate()
        existing_session = CashSession.objects.select_for_update().filter(
            staff=request.user,
            date=today,
            status=CashSession.STATUS_OPEN,
        ).first()
        if existing_session:
            return Response({
                'error': True,
                'message': 'An open cash session already exists for today',
                'data': self.get_serializer(existing_session).data,
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data={
            'staff': request.user.id,
            'date': today,
            'opening_balance': opening_balance,
            'notes': request.data.get('notes', ''),
        })
        serializer.is_valid(raise_exception=True)
        session = serializer.save()

        ActivityLog.objects.create(
            user=request.user,
            action_type='cash_session_opened',
            description=f"Cash session opened for {today}",
            content_object=session,
            metadata={
                'old_value': None,
                'new_value': CashSession.STATUS_OPEN,
                'amount': str(session.opening_balance),
                'opening_balance': str(session.opening_balance),
                'session_id': session.id,
            }
        )

        return Response({
            'error': False,
            'message': 'Cash session opened successfully',
            'data': self.get_serializer(session).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        session = self.get_queryset().filter(
            staff=request.user,
            status=CashSession.STATUS_OPEN,
        ).order_by('-date', '-id').first()

        if not session:
            return Response({
                'error': True,
                'message': 'No active cash session found'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'error': False,
            'message': 'Current cash session retrieved successfully',
            'data': {
                'session': self.get_serializer(session).data,
                'movements': CashMovementSerializer(session.movements.all(), many=True).data,
            }
        })

    @action(detail=True, methods=['post'], url_path='close')
    @transaction.atomic
    def close(self, request, pk=None):
        actual_closing_balance = request.data.get('actual_closing_balance')
        if actual_closing_balance is None:
            return Response({
                'error': True,
                'message': 'actual_closing_balance field is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        session = CashSession.objects.select_for_update().get(pk=self.get_object().pk)
        if session.staff_id != request.user.id and not request.user.is_superuser:
            return Response({
                'error': True,
                'message': 'You can only close your own cash session'
            }, status=status.HTTP_403_FORBIDDEN)

        if session.status != CashSession.STATUS_OPEN:
            return Response({
                'error': True,
                'message': 'Only open cash sessions can be closed'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            actual_closing = Decimal(str(actual_closing_balance))
        except Exception:
            return Response({
                'error': True,
                'message': 'actual_closing_balance must be a valid decimal amount'
            }, status=status.HTTP_400_BAD_REQUEST)

        reconciliation = close_cash_session(
            request,
            session,
            actual_closing,
            notes=request.data.get('notes') if request.data.get('notes') is not None else None
        )

        return Response({
            'error': False,
            'message': 'Cash session closed successfully',
            'data': {
                'session': self.get_serializer(session).data,
                'reconciliation': CashReconciliationSerializer(reconciliation).data,
            }
        })


class PaymentCollectionViewSet(viewsets.GenericViewSet):
    """
    Staff cash payment collection and manager verification endpoints.
    """
    queryset = CashMovement.objects.select_related(
        'session',
        'session__staff',
        'booking',
        'booking__customer',
        'booking__vehicle_model',
        'recorded_by',
        'verified_by',
    ).all()
    serializer_class = CashMovementSerializer

    def get_permissions(self):
        if self.action == 'verify':
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated(), IsStaffAuthenticated()]

    @action(detail=False, methods=['post'], url_path='collect')
    @transaction.atomic
    def collect(self, request):
        booking_id = request.data.get('booking_id')
        amount = request.data.get('amount')
        if not booking_id or amount is None:
            return Response({
                'error': True,
                'message': 'booking_id and amount are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({
                'error': True,
                'message': 'amount must be a valid decimal amount'
            }, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({
                'error': True,
                'message': 'amount must be greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.select_for_update().get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({
                'error': True,
                'message': 'Booking not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if booking.payment_method != 'cash':
            return Response({
                'error': True,
                'message': 'Only cash bookings can be collected through this endpoint'
            }, status=status.HTTP_400_BAD_REQUEST)

        session = CashSession.objects.select_for_update().filter(
            staff=request.user,
            status=CashSession.STATUS_OPEN,
        ).order_by('-date', '-id').first()
        if not session:
            return Response({
                'error': True,
                'message': 'No open cash session found for current staff'
            }, status=status.HTTP_400_BAD_REQUEST)

        existing_collection = CashMovement.objects.filter(
            session=session,
            booking=booking,
            movement_type=CashMovement.TYPE_COLLECTION,
        ).first()
        if existing_collection:
            return Response({
                'error': True,
                'message': 'Cash has already been collected for this booking in the current session',
                'data': self.get_serializer(existing_collection).data,
            }, status=status.HTTP_400_BAD_REQUEST)

        movement = CashMovement.objects.create(
            session=session,
            movement_type=CashMovement.TYPE_COLLECTION,
            booking=booking,
            amount=amount,
            description=request.data.get('description', f"Cash collected for Booking #{booking.id}"),
            recorded_by=request.user,
        )
        booking.payment_status = 'completed'
        booking.save(update_fields=['payment_status', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='cash_collected',
            description=f"Collected cash payment of {amount} for Booking #{booking.id}",
            content_object=movement,
            metadata={
                'old_value': 'pending',
                'new_value': booking.payment_status,
                'booking_id': booking.id,
                'cash_movement_id': movement.id,
                'amount': str(amount),
                'session_id': session.id,
            }
        )

        return Response({
            'error': False,
            'message': 'Cash collection recorded successfully',
            'data': self.get_serializer(movement).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='verify')
    @transaction.atomic
    def verify(self, request, pk=None):
        movement = CashMovement.objects.select_for_update().get(pk=self.get_object().pk)
        if movement.movement_type != CashMovement.TYPE_COLLECTION:
            return Response({
                'error': True,
                'message': 'Only cash collection movements can be verified'
            }, status=status.HTTP_400_BAD_REQUEST)

        movement.verification_status = CashMovement.VERIFICATION_VERIFIED
        movement.verified_by = request.user
        movement.verified_at = timezone.now()
        movement.save(update_fields=['verification_status', 'verified_by', 'verified_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='payment_verified',
            description=f"Verified cash movement #{movement.id}",
            content_object=movement,
            metadata={
                'old_value': CashMovement.VERIFICATION_PENDING,
                'new_value': movement.verification_status,
                'cash_movement_id': movement.id,
                'booking_id': movement.booking_id,
                'amount': str(movement.amount),
                'session_id': movement.session_id,
            }
        )

        return Response({
            'error': False,
            'message': 'Payment verified successfully',
            'data': self.get_serializer(movement).data,
        })

    @action(detail=False, methods=['get'], url_path='pending-reconciliation')
    def pending_reconciliation(self, request):
        session = CashSession.objects.filter(
            staff=request.user,
            status=CashSession.STATUS_OPEN,
        ).order_by('-date', '-id').first()
        if not session:
            return Response({
                'error': False,
                'message': 'No open cash session found',
                'data': [],
            })

        movements = self.get_queryset().filter(session=session)
        return Response({
            'error': False,
            'message': 'Pending reconciliation movements retrieved successfully',
            'data': [
                {
                    **CashMovementSerializer(movement).data,
                    'booking_detail': BookingDetailSerializer(movement.booking).data if movement.booking else None,
                }
                for movement in movements
            ],
            'session': CashSessionSerializer(session).data,
        })


class CashReconciliationViewSet(viewsets.GenericViewSet):
    """
    Backward-compatible cash reconciliation endpoints for admin/staff clients.
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffAuthenticated]
    queryset = CashReconciliation.objects.select_related(
        'session',
        'session__staff',
        'reconciled_by',
    ).all()
    serializer_class = CashReconciliationSerializer

    @transaction.atomic
    def create(self, request):
        actual_closing_balance = request.data.get('actual_closing_balance', request.data.get('total_collected'))
        if actual_closing_balance is None:
            return Response({
                'error': True,
                'message': 'actual_closing_balance field is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        session = CashSession.objects.select_for_update().filter(
            staff=request.user,
            status=CashSession.STATUS_OPEN,
        ).order_by('-date', '-id').first()
        if not session:
            return Response({
                'error': True,
                'message': 'No open cash session found for current staff'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            actual_closing = Decimal(str(actual_closing_balance))
        except Exception:
            return Response({
                'error': True,
                'message': 'actual_closing_balance must be a valid decimal amount'
            }, status=status.HTTP_400_BAD_REQUEST)

        reconciliation = close_cash_session(
            request,
            session,
            actual_closing,
            notes=request.data.get('notes') if request.data.get('notes') is not None else None
        )

        ActivityLog.objects.create(
            user=request.user,
            action_type='cash_reconciled',
            description=f"Cash reconciled for session #{session.id}",
            content_object=reconciliation,
            metadata={
                'old_value': CashSession.STATUS_OPEN,
                'new_value': session.status,
                'amount': str(actual_closing),
                'session_id': session.id,
                'reconciliation_id': reconciliation.id,
                'expected_closing': str(session.expected_closing),
                'actual_closing': str(session.closing_balance),
                'variance': str(session.variance),
            }
        )

        return Response({
            'error': False,
            'message': 'Cash reconciled successfully',
            'data': {
                'session': CashSessionSerializer(session).data,
                'reconciliation': self.get_serializer(reconciliation).data,
            }
        })

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        since = timezone.localdate() - timedelta(days=30)
        queryset = self.get_queryset().filter(session__date__gte=since)

        staff_id = request.query_params.get('staff')
        if staff_id:
            queryset = queryset.filter(session__staff_id=staff_id)

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(session__status=status_filter)

        date_range = request.query_params.get('date_range')
        if date_range and ',' in date_range:
            start_date, end_date = [part.strip() for part in date_range.split(',', 1)]
            queryset = queryset.filter(session__date__range=[start_date, end_date])
        else:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date:
                queryset = queryset.filter(session__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(session__date__lte=end_date)

        return Response({
            'error': False,
            'message': 'Cash reconciliation history retrieved successfully',
            'data': self.get_serializer(queryset, many=True).data,
        })


class StaffBookingViewSet(viewsets.ModelViewSet):
    """
    API for Staff and Managers to view and update repair bookings.
    - Mechanics see only assigned bookings.
    - Managers/Admins see all bookings.
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffAuthenticated]
    queryset = Booking.objects.select_related(
        'customer', 
        'vehicle_model__vehicle_brand__vehicle_type'
    ).prefetch_related(
        'booking_services__service__service_category',
        'booking_parts__spare_part'
    ).all().order_by('-created_at')
    
    serializer_class = BookingDetailSerializer

    VALID_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['in_progress', 'cancelled'],
        'in_progress': ['completed', 'cancelled'],
        'completed': [],
        'cancelled': [],
    }

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = request.user
        qs = self.get_queryset()
        
        from django.utils import timezone
        today = timezone.now().date()
        
        return Response({
            'total_assigned': qs.count(),
            'pending': qs.filter(
                booking_status='pending'
            ).count(),
            'in_progress': qs.filter(
                booking_status='in_progress'
            ).count(),
            'completed_today': qs.filter(
                booking_status='completed',
                updated_at__date=today
            ).count(),
            'cash_collected_today': 0,
        })

    def get_queryset(self):
        user = self.request.user
        qs = Booking.objects.all().select_related(
            'customer', 'vehicle_model'
        ).order_by('-created_at')
        
        # Superusers and managers see everything
        if user.is_superuser or getattr(user, 'is_manager', False):
            mechanic_id = self.request.query_params.get(
                'mechanic_id'
            )
            if mechanic_id:
                qs = qs.filter(mechanic_id=mechanic_id)
            return qs
        
        # Regular staff (mechanics) see only their jobs
        if user.is_staff:
            return qs.filter(mechanic=user)
        
        # Everyone else: nothing
        return qs.none()

    def list(self, request, *args, **kwargs):
        status_filter = request.query_params.get('status')
        date_filter = request.query_params.get('date')
        search = request.query_params.get('search')
        payment_method = request.query_params.get('payment_method')
        payment_status = request.query_params.get('payment_status')
        
        queryset = self.get_queryset()
        
        if status_filter:
            queryset = queryset.filter(booking_status=status_filter)
        if date_filter:
            queryset = queryset.filter(appointment_date=date_filter)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        if search:
            queryset = queryset.filter(
                Q(customer__name__icontains=search) |
                Q(customer__phone__icontains=search)
            )
            
        queryset = queryset.order_by('appointment_date', 'appointment_time', '-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Staff bookings retrieved successfully',
            'data': serializer.data,
            'count': queryset.count()
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'error': False,
            'message': 'Booking details retrieved successfully',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='update-status')
    @transaction.atomic
    def update_status(self, request, pk=None):
        booking = self.get_object()
        old_status = booking.booking_status
        new_status = request.data.get('status')
        notes = (request.data.get('notes') or '').strip()
        
        if not new_status:
            return Response({'error': 'status field is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if old_status in ['completed', 'cancelled']:
            return Response(
                {
                    'error': f'Booking is already in terminal state: {old_status}',
                    'code': 'TERMINAL_STATE',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_statuses = self.VALID_TRANSITIONS.get(old_status, [])
        if new_status not in allowed_statuses:
            return Response(
                {
                    'error': f'Cannot transition booking from {old_status} to {new_status}',
                    'code': 'INVALID_TRANSITION',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.booking_status = new_status
        if notes:
            note_header = timezone.now().strftime('%Y-%m-%d %H:%M')
            user_label = request.user.get_username() if request.user and request.user.is_authenticated else 'system'
            appended_note = f'[{note_header}] Status {old_status} -> {new_status} by {user_label}: {notes}'
            booking.internal_notes = (
                f'{booking.internal_notes}\n\n{appended_note}'
                if booking.internal_notes
                else appended_note
            )
        booking.save()

        # ASSUMPTION: ActivityLog uses user/action_type/content_object rather than
        # action/booking/performed_by, and action_type is limited to existing choices.
        ActivityLog.objects.create(
            user=request.user,
            action_type='status_change',
            description=f"Status changed from {old_status} to {new_status} for Booking #{booking.id}",
            content_object=booking,
            metadata={
                'from': old_status,
                'to': new_status,
                'notes': notes,
                'old_value': old_status,
                'new_value': new_status,
                'booking_id': booking.id,
            }
        )
        
        return Response({'error': False, 'message': f'Status updated to {new_status}', 'data': self.get_serializer(booking).data})

    @action(detail=True, methods=['post'], url_path='add-part')
    @transaction.atomic
    def add_part(self, request, pk=None):
        part_id = request.data.get('spare_part_id') or request.data.get('part_id')
        try:
            quantity = int(request.data.get('quantity', 1))
        except (TypeError, ValueError):
            return Response({'error': True, 'message': 'quantity must be a valid integer'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response({'error': True, 'message': 'quantity must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
            part = SparePart.objects.select_for_update().get(id=part_id)
        except Booking.DoesNotExist:
            return Response({'error': True, 'message': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
        except SparePart.DoesNotExist:
            return Response({'error': True, 'message': 'Part not found'}, status=status.HTTP_404_NOT_FOUND)

        if booking.booking_status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Cannot add parts to a completed or cancelled booking', 'code': 'BOOKING_TERMINAL'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not part.in_stock:
            return Response(
                {'error': True, 'message': f'{part.name} is out of stock'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if part.stock_qty < quantity:
            return Response({
                'error': True,
                'message': f'Insufficient stock for {part.name}. Available: {part.stock_qty}',
                'details': {'part_id': part.id, 'available_stock': part.stock_qty, 'requested_quantity': quantity}
            }, status=status.HTTP_400_BAD_REQUEST)

        locked_price = part.sale_price
        booking_part = BookingPart.objects.create(
                booking=booking,
                spare_part=part,
                unit_price=locked_price,
                quantity=quantity,
                approval_status=BookingPart.APPROVAL_PENDING,
        )
        booking.total_amount += booking_part.total_price
        booking.save(update_fields=['total_amount', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='part_added',
            description=f"Added {quantity}x {part.name} to Booking #{booking.id}",
            content_object=booking_part,
            metadata={
                'old_value': None,
                'new_value': booking_part.approval_status,
                'booking_id': booking.id,
                'booking_part_id': booking_part.id,
                'part_id': part.id,
                'part_name': part.name,
                'quantity': quantity,
                'amount': str(booking_part.total_price),
                'locked_unit_price': str(locked_price),
                'approval_status': booking_part.approval_status,
            }
        )
        ActivityLog.objects.create(
            user=request.user,
            action_type='price_locked',
            description=f"Locked price {locked_price} for {part.name} on Booking #{booking.id}",
            content_object=booking_part,
            metadata={
                'old_value': str(part.sale_price),
                'new_value': str(locked_price),
                'booking_id': booking.id,
                'booking_part_id': booking_part.id,
                'part_id': part.id,
                'quantity': quantity,
                'amount': str(booking_part.total_price),
                'locked_unit_price': str(locked_price),
                'price_locked_at': booking_part.price_locked_at.isoformat() if booking_part.price_locked_at else None,
            }
        )

        return Response({'error': False, 'message': 'Part added pending approval', 'data': BookingDetailSerializer(booking).data})

    @action(detail=True, methods=['post'], url_path='add-service')
    @transaction.atomic
    def add_service(self, request, pk=None):
        service_id = request.data.get('service_id') or request.data.get('service')
        if not service_id:
            return Response({'error': True, 'message': 'service_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': True, 'message': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        if booking.booking_status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Cannot add services to a completed or cancelled booking', 'code': 'BOOKING_TERMINAL'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return Response({'error': True, 'message': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)

        if BookingService.objects.filter(booking=booking, service=service).exists():
            return Response(
                {'error': True, 'message': f'{service.name} is already added to this booking', 'code': 'SERVICE_ALREADY_ADDED'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        custom_price = request.data.get('custom_price')
        if custom_price is not None:
            user = request.user
            if not (getattr(user, 'is_superuser', False) or getattr(user, 'is_manager', False)):
                return Response(
                    {'error': True, 'message': 'Only managers or admins can override service price'},
                    status=status.HTTP_403_FORBIDDEN
                )
            try:
                service_price = Decimal(str(custom_price))
                if service_price < Decimal('0.00'):
                    return Response({'error': True, 'message': 'custom_price cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
            except (TypeError, ValueError, InvalidOperation):
                return Response({'error': True, 'message': 'Invalid custom_price format'}, status=status.HTTP_400_BAD_REQUEST)

        else:
            try:
                pricing = ServicePricing.objects.get(
                    service=service,
                    vehicle_model=booking.vehicle_model
                )
                service_price = pricing.price
            except ServicePricing.DoesNotExist:
                return Response({
                    'error': True,
                    'message': f'Service pricing not found for {service.name} and selected vehicle model'
                }, status=status.HTTP_400_BAD_REQUEST)

        booking_service = BookingService.objects.create(
            booking=booking,
            service=service,
            price=service_price,
        )

        booking.total_amount += service_price
        booking.save(update_fields=['total_amount', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='service_added',
            description=f"Added service {service.name} (₹{service_price}) to Booking #{booking.id}",
            content_object=booking_service,
            metadata={
                'booking_id': booking.id,
                'booking_service_id': booking_service.id,
                'service_id': service.id,
                'service_name': service.name,
                'amount': str(service_price),
            }
        )

        return Response({
            'error': False,
            'message': 'Service added successfully',
            'data': BookingDetailSerializer(booking).data
        })

    @action(detail=True, methods=['post'], url_path='remove-part')
    @transaction.atomic
    def remove_part(self, request, pk=None):
        bp_id = request.data.get('booking_part_id')
        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': True, 'message': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            bp = BookingPart.objects.select_for_update().select_related('spare_part').get(id=bp_id, booking=booking)
        except BookingPart.DoesNotExist:
            return Response({'error': True, 'message': 'Part not found'}, status=status.HTTP_404_NOT_FOUND)

        if bp.approval_status == BookingPart.APPROVAL_APPROVED and not request.user.is_superuser:
            return Response({
                'error': True,
                'message': 'Approved parts require admin permission or customer re-approval before removal'
            }, status=status.HTTP_403_FORBIDDEN)

        if bp.approval_status != BookingPart.APPROVAL_PENDING:
            return Response(
                {'error': 'Only pending parts can be removed', 'code': 'PART_NOT_PENDING'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        part_name = bp.spare_part.name
        removed_total = bp.total_price
        booking.total_amount -= removed_total
        if booking.total_amount < 0:
            booking.total_amount = Decimal('0.00')
        bp.delete()
        booking.save(update_fields=['total_amount', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='part_removed',
            description=f"Removed {part_name} from Booking #{booking.id}",
            content_object=booking,
            metadata={
                'old_value': bp.approval_status,
                'new_value': 'removed',
                'booking_id': booking.id,
                'booking_part_id': bp_id,
                'part_name': part_name,
                'amount': str(removed_total),
                'removed_total': str(removed_total),
                'approval_status': bp.approval_status,
            }
        )

        return Response({'error': False, 'message': 'Part removed', 'data': BookingDetailSerializer(booking).data})

    @action(detail=True, methods=['delete'], url_path='remove-part/(?P<booking_part_id>[^/.]+)')
    @transaction.atomic
    def delete_part(self, request, pk=None, booking_part_id=None):
        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': True, 'message': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            bp = BookingPart.objects.select_for_update().select_related('spare_part').get(id=booking_part_id, booking=booking)
        except BookingPart.DoesNotExist:
            return Response({'error': 'Booking part does not belong to this booking', 'code': 'BOOKING_PART_MISMATCH'}, status=status.HTTP_400_BAD_REQUEST)

        if booking.booking_status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Cannot remove parts from a completed or cancelled booking', 'code': 'BOOKING_TERMINAL'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if bp.approval_status != BookingPart.APPROVAL_PENDING:
            return Response(
                {'error': 'Only pending parts can be removed', 'code': 'PART_NOT_PENDING'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        part_name = bp.spare_part.name
        removed_total = bp.total_price
        booking.total_amount -= removed_total
        if booking.total_amount < 0:
            booking.total_amount = Decimal('0.00')
        bp.delete()
        booking.save(update_fields=['total_amount', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='part_removed',
            description=f"Removed {part_name} from Booking #{booking.id}",
            content_object=booking,
            metadata={
                'old_value': BookingPart.APPROVAL_PENDING,
                'new_value': 'removed',
                'booking_id': booking.id,
                'booking_part_id': booking_part_id,
                'part_name': part_name,
                'amount': str(removed_total),
            }
        )

        booking = self.get_queryset().get(pk=booking.pk)
        return Response({'error': False, 'message': 'Part removed', 'data': BookingDetailSerializer(booking).data})

    @action(detail=True, methods=['post'], url_path='approve-part/(?P<booking_part_id>[^/.]+)')
    @transaction.atomic
    def approve_part(self, request, pk=None, booking_part_id=None):
        return self._set_booking_part_approval(
            request=request,
            pk=pk,
            booking_part_id=booking_part_id,
            target_status=BookingPart.APPROVAL_APPROVED,
            already_code='ALREADY_APPROVED',
            # ASSUMPTION: ActivityLog.action_type is max_length=20, so use
            # the existing shorter choice and keep the requested name in metadata.
            action_type='part_approved',
            verb='approved',
            requested_action='booking_part_approved',
        )

    @action(detail=True, methods=['post'], url_path='reject-part/(?P<booking_part_id>[^/.]+)')
    @transaction.atomic
    def reject_part(self, request, pk=None, booking_part_id=None):
        return self._set_booking_part_approval(
            request=request,
            pk=pk,
            booking_part_id=booking_part_id,
            target_status=BookingPart.APPROVAL_REJECTED,
            already_code='ALREADY_REJECTED',
            # ASSUMPTION: ActivityLog.action_type is max_length=20, so use
            # the existing shorter choice and keep the requested name in metadata.
            action_type='part_rejected',
            verb='rejected',
            requested_action='booking_part_rejected',
        )

    def _set_booking_part_approval(self, request, pk, booking_part_id, target_status, already_code, action_type, verb, requested_action):
        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response({'error': True, 'message': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            booking_part = BookingPart.objects.select_for_update().select_related('spare_part').get(
                id=booking_part_id,
                booking=booking,
            )
        except BookingPart.DoesNotExist:
            return Response(
                {'error': 'Booking part does not belong to this booking', 'code': 'BOOKING_PART_MISMATCH'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.booking_status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Cannot change parts on a completed or cancelled booking', 'code': 'BOOKING_TERMINAL'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking_part.approval_status == target_status:
            return Response(
                {'error': f'Booking part is already {verb}', 'code': already_code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = booking_part.approval_status
        booking_part.approval_status = target_status
        if target_status == BookingPart.APPROVAL_APPROVED:
            booking_part.approved_by = request.user
            booking_part.approved_at = timezone.now()
            update_fields = ['approval_status', 'approved_by', 'approved_at']
        else:
            booking_part.approved_by = request.user
            booking_part.approved_at = timezone.now()
            update_fields = ['approval_status', 'approved_by', 'approved_at']
        booking_part.save(update_fields=update_fields)

        # ASSUMPTION: ActivityLog uses user/action_type/content_object rather than
        # action/booking/performed_by, and BookingPart's locked price field is unit_price.
        ActivityLog.objects.create(
            user=request.user,
            action_type=action_type,
            description=f"{booking_part.spare_part.name} {verb} for Booking #{booking.id}",
            content_object=booking_part,
            metadata={
                'from': old_status,
                'to': target_status,
                'old_value': old_status,
                'new_value': target_status,
                'booking_id': booking.id,
                'booking_part_id': booking_part.id,
                'action': requested_action,
                'part': booking_part.spare_part.name,
                'part_id': booking_part.spare_part_id,
                'price': str(booking_part.unit_price),
                'quantity': booking_part.quantity,
                'amount': str(booking_part.total_price),
            }
        )

        return Response({
            'error': False,
            'message': f'Booking part {verb}',
            'data': BookingPartSerializer(booking_part).data,
        })


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for Admins to view system activity logs
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    queryset = ActivityLog.objects.select_related('user', 'content_type').prefetch_related('content_object').order_by('-timestamp')
    serializer_class = ActivityLogSerializer
    pagination_class = ActivityLogPagination

    def get_filtered_queryset(self):
        request = self.request
        queryset = self.get_queryset()

        action_type = request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)

        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        booking_id = request.query_params.get('booking_id')
        if booking_id:
            try:
                booking_id_int = int(booking_id)
            except (TypeError, ValueError):
                booking_id_int = None
            if booking_id_int is None:
                return queryset.none()
            booking_content_type = ContentType.objects.get_for_model(Booking)
            booking_part_content_type = ContentType.objects.get_for_model(BookingPart)
            queryset = queryset.filter(
                Q(content_type=booking_content_type, object_id=booking_id_int) |
                Q(content_type=booking_part_content_type, metadata__booking_id=booking_id_int) |
                Q(metadata__booking_id=booking_id_int)
            )

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        return queryset.order_by('-timestamp')

    def list(self, request, *args, **kwargs):
        queryset = self.get_filtered_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'data': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        queryset = self.get_filtered_queryset()
        counts = queryset.values('action_type').annotate(count=Count('id')).order_by('action_type')
        return Response({
            'error': False,
            'message': 'Activity log summary retrieved successfully',
            'data': list(counts),
        })
