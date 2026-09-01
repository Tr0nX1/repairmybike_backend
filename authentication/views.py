import uuid
import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.db import transaction, models
from django.db.models import Q, Count, Max, OuterRef, Subquery, Prefetch, Sum
from django.db.models.functions import Cast, Coalesce
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from descope import DescopeClient, DeliveryMethod, SESSION_TOKEN_NAME, REFRESH_SESSION_TOKEN_NAME
from .models import UserSession, PhoneOTP, EmailOTP, OTPAttempt, StaffDirectory, UserAddress, ContactSubmission
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    UserProfileUpdateSerializer, PhoneOTPRequestSerializer,
    PhoneOTPVerifySerializer, PhoneLoginSerializer,
    EmailOTPRequestSerializer, EmailOTPVerifySerializer, EmailLoginSerializer,
    UnifiedOTPRequestSerializer, UnifiedOTPVerifySerializer,
    StaffOtpLoginSerializer,
    StaffPasswordLoginSerializer,
    UserAddressSerializer,
    StaffDirectorySerializer,
    CustomerCRMSerializer,
    ContactSubmissionSerializer
)
from .authentication import DescopeAuthentication
from bookings.models import Booking, Customer
from subscriptions.models import Subscription

User = get_user_model()
logger = logging.getLogger(__name__)

def create_descope_client():
    return DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)

def _merge_guest_data(user, guest_id):
    """
    Merge guest data (bookings, etc.) associated with guest_id into the user account.
    """
    if not guest_id:
        return
    
    try:
        from .models import GuestSession
        guest_session = GuestSession.objects.filter(guest_id=guest_id).first()
        if not guest_session:
            return
            
        logger.info(f"Merging guest data for guest_id: {guest_id} into user: {user.id}")

        # Update cart
        from spare_parts.models import Cart
        Cart.objects.filter(session_id=str(guest_session.guest_id), user__isnull=True).update(user=user)

        # Update saved services
        from services.models import GuestSavedService, UserSavedService
        guest_saved_services = GuestSavedService.objects.filter(guest_session=guest_session)
        for item in guest_saved_services:
            UserSavedService.objects.get_or_create(user=user, service=item.service)
        guest_saved_services.delete()

        # Update saved items
        from spare_parts.models import GuestSavedPart, UserSavedPart
        guest_saved = GuestSavedPart.objects.filter(guest_session=guest_session)
        for item in guest_saved:
            UserSavedPart.objects.get_or_create(user=user, spare_part=item.spare_part)
        guest_saved.delete()

    except Exception as e:
        logger.error(f"Error merging guest data: {e}")

def get_or_create_user_from_auth_response(auth_response, phone_number=None, email=None, guest_id=None):
    """
    Helper to get or create a user from a Descope auth response.
    Returns (user, created)
    """
    user_id = auth_response.get('user', {}).get('userId')
    if not user_id:
        raise ValueError("No userId in Descope response")

    # 1. Try to get user by descope_user_id
    try:
        user = User.objects.get(descope_user_id=user_id)
        if phone_number:
            user.phone_number = phone_number
            user.is_phone_verified = True
        if email:
            user.email = email
            user.is_verified = True
        user.save()
        _merge_guest_data(user, guest_id)
        return user, False
    except User.DoesNotExist:
        pass

    # 2. Try to get user by phone/email to link existing accounts
    if phone_number:
        try:
            user = User.objects.get(phone_number=phone_number)
            user.descope_user_id = user_id
            user.is_phone_verified = True
            user.save()
            _merge_guest_data(user, guest_id)
            return user, False
        except User.DoesNotExist:
            pass
            
    if email:
        try:
            user = User.objects.get(email=email)
            user.descope_user_id = user_id
            user.is_verified = True
            user.save()
            _merge_guest_data(user, guest_id)
            return user, False
        except User.DoesNotExist:
            pass

    # 3. Create new user
    if phone_number:
        username = f"user_{phone_number.replace('+', '').replace('-', '')}"
    else:
        username = email.split('@')[0] if email else f"user_{user_id[:8]}"
        
    user = User.objects.create_user(
        username=username,
        email=email or '',
        phone_number=phone_number or '',
        descope_user_id=user_id,
        is_phone_verified=bool(phone_number),
        is_verified=True
    )
    _merge_guest_data(user, guest_id)
    return user, True


class ContactSubmissionViewSet(viewsets.ModelViewSet):
    queryset = ContactSubmission.objects.all()
    serializer_class = ContactSubmissionSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), permissions.IsAdminUser()]

    def perform_create(self, serializer):
        """
        Link contact submission to authenticated user if available.
        This prevents logout issues when authenticated users submit contact forms.
        """
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
            logger.info(f"Contact submission created by user: {self.request.user.id} ({self.request.user.email})")
        else:
            serializer.save()
            logger.info("Guest contact submission created")

    def create(self, request, *args, **kwargs):
        """
        Override create to return consistent response format with authentication preserved.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return success response with consistent format
        return Response({
            'error': False,
            'message': 'Contact submission created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

class StaffDirectoryViewSet(viewsets.ModelViewSet):
    """ViewSet for StaffDirectory model"""
    queryset = StaffDirectory.objects.all().order_by('-created_at')
    serializer_class = StaffDirectorySerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['role', 'is_active']
    search_fields = ['name', 'employee_id', 'role', 'identifier']
    ordering_fields = ['name', 'created_at']

    def perform_create(self, serializer):
        photo = self.request.FILES.get('photo')
        if photo:
            serializer.save(photo=photo)
        else:
            serializer.save()

    def perform_update(self, serializer):
        photo = self.request.FILES.get('photo')
        if photo:
            serializer.save(photo=photo)
        else:
            serializer.save()

class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Customer CRM"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    search_fields = ['first_name', 'last_name', 'email', 'phone_number']
    ordering_fields = ['total_ltv', 'created_at', 'last_visit']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            from .serializers import CustomerDetailSerializer
            return CustomerDetailSerializer
        return CustomerCRMSerializer

    def get_queryset(self):
        # We only want users who have a phone number (customers)
        bookings_count_sq = Booking.objects.filter(
            customer__phone=OuterRef('phone_number')
        ).values('customer__phone').annotate(
            count=Count('id', distinct=True)
        ).values('count')

        total_spent_sq = Booking.objects.filter(
            customer__phone=OuterRef('phone_number'),
            booking_status='completed'
        ).values('customer__phone').annotate(
            total=Sum('total_amount')
        ).values('total')
        
        latest_visit_sq = Booking.objects.filter(
            customer__phone=OuterRef('phone_number')
        ).order_by('-appointment_date').values('appointment_date')[:1]
        
        return User.objects.filter(
            phone_number__isnull=False
        ).annotate(
            total_bookings=Coalesce(Subquery(bookings_count_sq, output_field=models.IntegerField()), Value(0)),
            total_spent=Coalesce(Subquery(total_spent_sq, output_field=models.DecimalField(max_digits=12, decimal_places=2)), Value(0.00, output_field=models.DecimalField(max_digits=12, decimal_places=2))),
            active_subscriptions=Count('subscriptions', filter=Q(subscriptions__status='active'), distinct=True),
            last_visit=Subquery(latest_visit_sq)
        ).prefetch_related(
            'addresses', 
            'vehicles', 
            'vehicles__vehicle_model', 
            'vehicles__vehicle_model__vehicle_brand'
        ).distinct().order_by('-created_at')

class UserProfileView(RetrieveUpdateAPIView):
    """Handle user profile retrieval and updates"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserProfileUpdateSerializer
        return UserSerializer

class UserProfileUploadView(APIView):
    """Handle profile picture upload separately"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'error': True, 'message': 'No photo provided'}, status=400)
        user.profile_picture = photo
        user.save()
        return Response({
            'error': False,
            'message': 'Profile picture updated successfully',
            'profile_picture_url': request.build_absolute_uri(user.profile_picture.url)
        })

class UserRegistrationView(APIView):
    """Handle user registration using Descope"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                descope_user = descope_client.user.create(
                    login_id=serializer.validated_data['email'],
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password'],
                    name=f"{serializer.validated_data.get('first_name', '')} {serializer.validated_data.get('last_name', '')}".strip(),
                    phone=serializer.validated_data.get('phone_number', '')
                )
                user = User.objects.create_user(
                    username=serializer.validated_data['email'],
                    email=serializer.validated_data['email'],
                    descope_user_id=descope_user['userId'],
                    first_name=serializer.validated_data.get('first_name', ''),
                    last_name=serializer.validated_data.get('last_name', ''),
                    phone_number=serializer.validated_data.get('phone_number', ''),
                    is_verified=False
                )
                return Response({
                    'message': 'User registered successfully',
                    'user': UserSerializer(user, context={'request': request}).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}")
                return Response({'error': 'Registration failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    """Handle user login using Descope"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response({
                'error': 'Password authentication not supported. Please use OTP authentication.',
                'redirect_to_otp': True,
                'message': 'Use /auth/otp/request/ endpoint for authentication'
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(APIView):
    """Handle user logout"""
    def post(self, request):
        try:
            descope_client = create_descope_client()
            refresh_token = request.data.get('refresh_token') if isinstance(request.data, dict) else None
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            session_token = auth_header.split(' ', 1)[1] if auth_header.startswith('Bearer ') else None
            if refresh_token:
                try:
                    descope_client.logout(refresh_token=refresh_token)
                except Exception as descope_err:
                    logger.warning(f"Descope logout failed: {descope_err}")
                UserSession.objects.filter(refresh_token=refresh_token).update(is_active=False)
            elif session_token:
                UserSession.objects.filter(session_token=session_token).update(is_active=False)
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return Response({'error': 'Logout failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PhoneOTPRequestView(APIView):
    """Handle phone OTP request using Descope"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = PhoneOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                phone_number = serializer.validated_data['phone_number']
                try:
                    descope_client.otp.sign_up_or_in(method=DeliveryMethod.SMS, login_id=phone_number)
                except Exception as descope_error:
                    logger.error(f"Descope OTP error: {str(descope_error)}")
                    return Response({'error': 'Failed to send verification code.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                PhoneOTP.objects.create(phone_number=phone_number, otp_code="****", expires_at=timezone.now() + timedelta(minutes=5))
                return Response({'message': 'Verification code sent successfully', 'phone_number': phone_number, 'expires_in': 300}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"OTP request failed: {str(e)}")
                return Response({'error': 'Failed to send OTP', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PhoneOTPVerifyView(APIView):
    """Handle phone OTP verification using Descope"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                phone_number = serializer.validated_data['phone_number']
                otp_code = serializer.validated_data['otp_code']
                auth_response = descope_client.otp.verify_code(method=DeliveryMethod.SMS, login_id=phone_number, code=otp_code)
                if auth_response:
                    guest_id = request.META.get('HTTP_X_GUEST_ID')
                    user, created = get_or_create_user_from_auth_response(auth_response, phone_number=phone_number, guest_id=guest_id)
                    PhoneOTP.objects.filter(phone_number=phone_number, is_verified=False).update(is_verified=True)
                    
                    session_jwt = auth_response.get("sessionToken", {}).get("jwt")
                    refresh_jwt = auth_response.get("refreshSessionToken", {}).get("jwt")
                    
                    if not session_jwt:
                         return Response({'error': 'No session token returned from Descope'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    UserSession.objects.update_or_create(
                        user=user, session_token=session_jwt,
                        defaults={'refresh_token': refresh_jwt, 'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True}
                    )
                    return Response({
                        'message': 'OTP verified successfully', 'user': UserSerializer(user, context={'request': request}).data,
                        'session_token': session_jwt, 'refresh_token': refresh_jwt
                    }, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"OTP verification failed: {str(e)}")
                return Response({'error': 'OTP verification failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PhoneLoginView(APIView):
    """Handle phone-based login with OTP"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                phone_number = serializer.validated_data['phone_number']
                otp_code = serializer.validated_data['otp_code']
                auth_response = descope_client.otp.verify_code(method=DeliveryMethod.SMS, login_id=phone_number, code=otp_code)
                if auth_response:
                    guest_id = request.META.get('HTTP_X_GUEST_ID')
                    user, created = get_or_create_user_from_auth_response(auth_response, phone_number=phone_number, guest_id=guest_id)
                    
                    session_jwt = auth_response.get("sessionToken", {}).get("jwt")
                    refresh_jwt = auth_response.get("refreshSessionToken", {}).get("jwt")
                    
                    UserSession.objects.update_or_create(
                        user=user, session_token=session_jwt,
                        defaults={'refresh_token': refresh_jwt, 'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True}
                    )
                    return Response({
                        'message': 'Login successful', 'user': UserSerializer(user, context={'request': request}).data,
                        'session_token': session_jwt, 'refresh_token': refresh_jwt
                    }, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                logger.error(f"Phone login failed: {str(e)}")
                return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailOTPRequestView(APIView):
    """Handle email OTP request using Descope"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = EmailOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                descope_client = create_descope_client()
                descope_client.otp.sign_up_or_in(method=DeliveryMethod.EMAIL, login_id=email)
                EmailOTP.objects.create(email=email, otp_code="****", expires_at=timezone.now() + timedelta(minutes=5))
                return Response({'message': 'Verification code sent successfully', 'email': email, 'expires_in': 300}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Email OTP request failed: {str(e)}")
                return Response({'error': 'Failed to send OTP', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailOTPVerifyView(APIView):
    """Handle email OTP verification using Descope"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = EmailOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                otp_code = serializer.validated_data['otp_code']
                descope_client = create_descope_client()
                auth_response = descope_client.otp.verify_code(method=DeliveryMethod.EMAIL, login_id=email, code=otp_code)
                if auth_response:
                    guest_id = request.META.get('HTTP_X_GUEST_ID')
                    user, created = get_or_create_user_from_auth_response(auth_response, email=email, guest_id=guest_id)
                    EmailOTP.objects.filter(email=email, is_verified=False).update(is_verified=True)
                    
                    session_jwt = auth_response.get("sessionToken", {}).get("jwt")
                    refresh_jwt = auth_response.get("refreshSessionToken", {}).get("jwt")
                    
                    UserSession.objects.update_or_create(
                        user=user, session_token=session_jwt,
                        defaults={
                            'refresh_token': refresh_jwt, 'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True,
                            'user_agent': request.META.get('HTTP_USER_AGENT'), 'ip_address': request.META.get('REMOTE_ADDR'), 'last_activity': timezone.now(),
                        }
                    )
                    return Response({
                        'message': 'OTP verified successfully', 'user': UserSerializer(user, context={'request': request}).data,
                        'session_token': session_jwt, 'refresh_token': refresh_jwt
                    }, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Email OTP verification failed: {str(e)}")
                return Response({'error': 'OTP verification failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailLoginView(APIView):
    """Handle email-based login with OTP"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                otp_code = serializer.validated_data['otp_code']
                descope_client = create_descope_client()
                auth_response = descope_client.otp.verify_code(method=DeliveryMethod.EMAIL, login_id=email, code=otp_code)
                if auth_response:
                    guest_id = request.META.get('HTTP_X_GUEST_ID')
                    user, created = get_or_create_user_from_auth_response(auth_response, email=email, guest_id=guest_id)
                    
                    session_jwt = auth_response.get("sessionToken", {}).get("jwt")
                    refresh_jwt = auth_response.get("refreshSessionToken", {}).get("jwt")
                    
                    UserSession.objects.update_or_create(
                        user=user, session_token=session_jwt,
                        defaults={'refresh_token': refresh_jwt, 'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True, 'last_activity': timezone.now()}
                    )
                    return Response({
                        'message': 'Login successful', 'user': UserSerializer(user, context={'request': request}).data,
                        'session_token': session_jwt, 'refresh_token': refresh_jwt
                    }, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as e:
                logger.error(f"Email login failed: {str(e)}")
                return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UnifiedOTPRequestView(APIView):
    """Handle unified OTP request (phone or email)"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = UnifiedOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                identifier = serializer.validated_data['identifier']
                method = serializer.validated_data['method']
                descope_client = create_descope_client()
                descope_method = DeliveryMethod.SMS if method == "phone" else DeliveryMethod.EMAIL
                descope_client.otp.sign_up_or_in(method=descope_method, login_id=identifier)
                if method == "phone":
                    PhoneOTP.objects.create(phone_number=identifier, otp_code="****", expires_at=timezone.now() + timedelta(minutes=5))
                else:
                    EmailOTP.objects.create(email=identifier, otp_code="****", expires_at=timezone.now() + timedelta(minutes=5))
                return Response({'message': 'OTP sent successfully', 'identifier': identifier, 'method': method, 'expires_in': 300}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Unified OTP request failed: {str(e)}")
                return Response({'error': 'Failed to send OTP', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UnifiedOTPVerifyView(APIView):
    """Handle unified OTP verification (phone or email)"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = UnifiedOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            try:
                identifier = serializer.validated_data['identifier']
                otp_code = serializer.validated_data['otp_code']
                method = serializer.validated_data['method']
                descope_client = create_descope_client()
                descope_method = DeliveryMethod.SMS if method == "phone" else DeliveryMethod.EMAIL
                auth_response = descope_client.otp.verify_code(method=descope_method, login_id=identifier, code=otp_code)
                if auth_response:
                    guest_id = request.META.get('HTTP_X_GUEST_ID')
                    if method == "phone":
                        user, created = get_or_create_user_from_auth_response(auth_response, phone_number=identifier, guest_id=guest_id)
                        PhoneOTP.objects.filter(phone_number=identifier, is_verified=False).update(is_verified=True)
                    else:
                        user, created = get_or_create_user_from_auth_response(auth_response, email=identifier, guest_id=guest_id)
                        EmailOTP.objects.filter(email=identifier, is_verified=False).update(is_verified=True)
                    
                    # Fix token extraction
                    session_token_data = auth_response.get("sessionToken", "")
                    refresh_token_data = auth_response.get("refreshSessionToken", "")
                    
                    if isinstance(session_token_data, dict):
                        session_jwt = session_token_data.get("jwt")
                    else:
                        session_jwt = session_token_data
                        
                    if isinstance(refresh_token_data, dict):
                        refresh_jwt = refresh_token_data.get("jwt")
                    else:
                        refresh_jwt = refresh_token_data
                    
                    if not session_jwt:
                         return Response({'error': 'No session token returned from Descope'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    UserSession.objects.update_or_create(
                        user=user, session_token=session_jwt,
                        defaults={'refresh_token': refresh_jwt, 'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True}
                    )
                    return Response({
                        'message': 'OTP verified successfully', 'user': UserSerializer(user, context={'request': request}).data,
                        'session_token': session_jwt, 'refresh_token': refresh_jwt
                    }, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Unified OTP verification failed: {str(e)}")
                return Response({'error': 'OTP verification failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RefreshTokenView(APIView):
    """Handle token refresh using Descope refresh token"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        refresh_token = request.data.get('refresh_token') or request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            descope_client = create_descope_client()
            auth_response = descope_client.refresh_session(refresh_token)
            if not auth_response:
                return Response({'error': 'Token refresh failed'}, status=status.HTTP_401_UNAUTHORIZED)
            
            session_jwt = auth_response.get("sessionToken", {}).get("jwt")
            new_refresh_jwt = auth_response.get("refreshSessionToken", {}).get("jwt")
            
            if new_refresh_jwt:
                UserSession.objects.filter(refresh_token=refresh_token).update(
                    session_token=session_jwt, refresh_token=new_refresh_jwt,
                    expires_at=timezone.now() + timedelta(hours=8), last_activity=timezone.now()
                )
            else:
                UserSession.objects.filter(refresh_token=refresh_token).update(session_token=session_jwt, last_activity=timezone.now())
            resp = {'session_token': session_jwt}
            if new_refresh_jwt:
                resp['refresh_token'] = new_refresh_jwt
            return Response(resp, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return Response({'error': 'Token refresh failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        return Response({'error': 'Password reset not supported. Please use OTP authentication.', 'redirect_to_otp': True}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        return Response({'error': 'Password update not supported.', 'redirect_to_otp': True}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_sessions(request):
    sessions = UserSession.objects.filter(user=request.user, is_active=True)
    return Response({'sessions': [{'id': s.id, 'created_at': s.created_at, 'expires_at': s.expires_at, 'is_active': s.is_active} for s in sessions]})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def revoke_session(request, session_id):
    try:
        session = UserSession.objects.get(id=session_id, user=request.user)
        session.is_active = False
        session.save()
        return Response({'message': 'Session revoked successfully'}, status=status.HTTP_200_OK)
    except UserSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def phone_verification_status(request):
    return Response({'is_phone_verified': request.user.is_phone_verified, 'phone_number': request.user.phone_number})

class StaffLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = StaffOtpLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method, identifier, otp_code, device_id = serializer.validated_data['method'], serializer.validated_data['identifier'], serializer.validated_data['otp_code'], serializer.validated_data.get('device_id')
        descope_client = create_descope_client()
        try:
            delivery = DeliveryMethod.SMS if method == 'sms' else DeliveryMethod.EMAIL
            auth_response = descope_client.otp.verify_code(method=delivery, login_id=identifier, code=otp_code)
            if not auth_response:
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_401_UNAUTHORIZED)
            try:
                user = User.objects.get((Q(email=identifier) | Q(phone_number=identifier)), is_active=True)
            except User.DoesNotExist:
                try:
                    directory_entry = StaffDirectory.objects.get(identifier=identifier, is_active=True)
                    username = identifier
                    email = identifier if '@' in identifier else ''
                    phone_number = '' if '@' in identifier else identifier
                    parts = directory_entry.name.split(' ', 1)
                    first_name, last_name = parts[0], parts[1] if len(parts) > 1 else ''
                    user = User.objects.create_user(username=username, email=email, first_name=first_name, last_name=last_name, phone_number=phone_number, is_active=True, is_staff=True)
                except StaffDirectory.DoesNotExist:
                    return Response({'error': 'User not found'}, status=status.HTTP_403_FORBIDDEN)
            if not (user.is_staff or user.is_superuser):
                return Response({'error': 'Staff privileges required'}, status=status.HTTP_403_FORBIDDEN)
            
            session_jwt = auth_response.get("sessionToken", {}).get("jwt")
            refresh_jwt = auth_response.get("refreshSessionToken", {}).get("jwt")
            
            UserSession.objects.update_or_create(user=user, session_token=session_jwt, defaults={'refresh_token': refresh_jwt, 'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True, 'device_id': device_id, 'user_agent': request.META.get('HTTP_USER_AGENT'), 'ip_address': request.META.get('REMOTE_ADDR'), 'last_activity': timezone.now()})
            return Response({'message': 'Staff login successful', 'user': UserSerializer(user, context={'request': request}).data, 'session_token': session_jwt, 'refresh_token': refresh_jwt}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

class StaffPasswordLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = StaffPasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier, password, device_id = serializer.validated_data['identifier'], serializer.validated_data['password'], serializer.validated_data.get('device_id')
        user = authenticate(request, username=identifier, password=password)
        if not user:
            try:
                candidate = User.objects.get(email=identifier); user = authenticate(request, username=candidate.username, password=password)
            except User.DoesNotExist: user = None
        if not user or not (user.is_staff or user.is_superuser):
            return Response({'error': 'Invalid credentials or permissions'}, status=status.HTTP_401_UNAUTHORIZED)
        token = uuid.uuid4().hex
        UserSession.objects.update_or_create(user=user, session_token=token, defaults={'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True, 'device_id': device_id, 'user_agent': request.META.get('HTTP_USER_AGENT'), 'ip_address': request.META.get('REMOTE_ADDR'), 'last_activity': timezone.now()})
        return Response({'message': 'Staff password login successful', 'user': UserSerializer(user, context={'request': request}).data, 'session_token': token}, status=status.HTTP_200_OK)

class AdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = StaffOtpLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method, identifier, otp_code, device_id = serializer.validated_data['method'], serializer.validated_data['identifier'], serializer.validated_data['otp_code'], serializer.validated_data.get('device_id')
        descope_client = create_descope_client()
        try:
            delivery = DeliveryMethod.SMS if method == 'sms' else DeliveryMethod.EMAIL
            auth_response = descope_client.otp.verify_code(method=delivery, login_id=identifier, code=otp_code)
            if not auth_response: return Response({'error': 'Invalid OTP code'}, status=status.HTTP_401_UNAUTHORIZED)
            try:
                user = User.objects.get((Q(email=identifier) | Q(phone_number=identifier)), is_active=True, is_superuser=True)
            except User.DoesNotExist: return Response({'error': 'Admin privileges required'}, status=status.HTTP_403_FORBIDDEN)
            
            session_jwt = auth_response.get("sessionToken", {}).get("jwt")
            refresh_jwt = auth_response.get("refreshSessionToken", {}).get("jwt")
            
            UserSession.objects.update_or_create(user=user, session_token=session_jwt, defaults={'refresh_token': refresh_jwt, 'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True, 'device_id': device_id, 'user_agent': request.META.get('HTTP_USER_AGENT'), 'ip_address': request.META.get('REMOTE_ADDR'), 'last_activity': timezone.now()})
            return Response({'message': 'Admin login successful', 'user': UserSerializer(user, context={'request': request}).data, 'session_token': session_jwt, 'refresh_token': refresh_jwt}, status=status.HTTP_200_OK)
        except Exception as e: return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

class AdminPasswordLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = StaffPasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier, password, device_id = serializer.validated_data['identifier'], serializer.validated_data['password'], serializer.validated_data.get('device_id')
        user = authenticate(request, username=identifier, password=password)
        if not user or not user.is_superuser: return Response({'error': 'Admin privileges required'}, status=status.HTTP_403_FORBIDDEN)
        token = uuid.uuid4().hex
        UserSession.objects.update_or_create(user=user, session_token=token, defaults={'expires_at': timezone.now() + timedelta(hours=8), 'is_active': True, 'device_id': device_id, 'user_agent': request.META.get('HTTP_USER_AGENT'), 'ip_address': request.META.get('REMOTE_ADDR'), 'last_activity': timezone.now()})
        return Response({'message': 'Admin password login successful', 'user': UserSerializer(user, context={'request': request}).data, 'session_token': token}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_phone_otp(request):
    phone_number = request.data.get('phone_number')
    if not phone_number: return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        descope_client = create_descope_client()
        descope_client.otp.sign_up_or_in(method=DeliveryMethod.SMS, login_id=phone_number)
        if request.user.phone_number != phone_number:
            request.user.phone_number = phone_number; request.user.save()
        return Response({'message': 'OTP resent successfully', 'phone_number': phone_number}, status=status.HTTP_200_OK)
    except Exception as e: return Response({'error': 'Failed to resend OTP', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserAddressViewSet(viewsets.ModelViewSet):
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self): return UserAddress.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        if serializer.validated_data.get('is_default', False): UserAddress.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)
    def perform_update(self, serializer):
        if serializer.validated_data.get('is_default', False): UserAddress.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save()

class FCMTokenUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        token = request.data.get('token')
        if not token: return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user; user.fcm_token = token; user.save(update_fields=['fcm_token', 'updated_at'])
        return Response({'error': False, 'message': 'FCM token updated successfully'})
