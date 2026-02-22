import uuid
import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.models import Group, Permission
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from descope import DescopeClient, DeliveryMethod, SESSION_TOKEN_NAME, REFRESH_SESSION_TOKEN_NAME
from .models import UserSession, PhoneOTP, EmailOTP, OTPAttempt, StaffDirectory, UserAddress, ContactMessage
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
    ContactMessageSerializer
)
from .authentication import DescopeAuthentication

logger = logging.getLogger(__name__)

# Added helper for Descope client with increased JWT leeway
JWT_LEEWAY_SECONDS = 30  # allow 30 seconds clock skew


def create_descope_client():
    """Create DescopeClient with increased jwt_validation_leeway."""
    return DescopeClient(
        project_id=settings.DESCOPE_PROJECT_ID,
        jwt_validation_leeway=JWT_LEEWAY_SECONDS
    )

User = get_user_model()


def _merge_guest_data(user, guest_id):
    """
    Merge data from a guest session into the authenticated user's account.
    """
    if not guest_id:
        return
    
    from .models import GuestSession
    from services.models import UserSavedService, GuestSavedService
    
    try:
        import uuid
        guest_uuid = uuid.UUID(guest_id)
        guest_session = GuestSession.objects.filter(guest_id=guest_uuid).first()
        
        if not guest_session:
            return

        # 1. Merge Saved Services
        guest_saved = GuestSavedService.objects.filter(guest_session=guest_session)
        for gs in guest_saved:
            # Create UserSavedService if not exists
            UserSavedService.objects.get_or_create(
                user=user,
                service=gs.service
            )
            #gs.delete() # We'll delete them after migration? Or just leave them.
            # Let's delete to clean up.
        
        guest_saved.delete()
        
        # 2. Merge Saved Spare Parts
        from spare_parts.models import UserSavedPart, GuestSavedPart
        guest_parts = GuestSavedPart.objects.filter(guest_session=guest_session)
        for gp in guest_parts:
            UserSavedPart.objects.get_or_create(
                user=user,
                spare_part=gp.spare_part
            )
        guest_parts.delete()
        
        # 3. Merge Context Data (e.g. cart from JSON)
        # In a real app, you'd translate JSON cart to DB Cart objects here.
        # For now, we'll just log or store in user context.
        
        # Finally, delete or deactivate guest session?
        # Typically we leave it but mark as merged or just delete.
        # guest_session.delete()

    except Exception as e:
        logger.error(f"Error merging guest data: {e}")


def _get_session_expiry():
    """Returns the standardized session expiry duration."""
    return timezone.now() + timedelta(days=30)


def _persist_user_session(user, auth_response, request, device_id=None):
    """
    Persist user session with metadata.
    """
    try:
        session_jwt = auth_response[SESSION_TOKEN_NAME]["jwt"]
        refresh_jwt = auth_response.get(REFRESH_SESSION_TOKEN_NAME, {}).get("jwt")
        
        UserSession.objects.update_or_create(
            user=user,
            session_token=session_jwt,
            defaults={
                'refresh_token': refresh_jwt,
                'expires_at': _get_session_expiry(),
                'is_active': True,
                'device_id': device_id or request.data.get('device_id'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'ip_address': request.META.get('REMOTE_ADDR'),
                'last_activity': timezone.now(),
            }
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to persist session: {e}")
        return False


def _sync_roles_and_permissions(user, auth_response):
    """
    Synchronize roles and permissions from Descope response to Django Groups.
    """
    # Descope returns roles/permissions in the user object or the main response
    user_data = auth_response.get('user', {})
    roles = user_data.get('roleNames', [])
    
    # Also check the JWT claims if available (e.g. from sessionToken)
    # But often the session 'user' object is easiest during login.
    
    if not roles:
        return

    for role_name in roles:
        group, created = Group.objects.get_or_create(name=role_name)
        if group not in user.groups.all():
            user.groups.add(group)
            logger.info(f"Synchronized role {role_name} for user {user.username}")

    # Update Django flags
    changed = False
    if 'admin' in [r.lower() for r in roles]:
        if not user.is_superuser:
            user.is_superuser = True
            user.is_staff = True
            changed = True
    elif 'staff' in [r.lower() for r in roles]:
        if not user.is_staff:
            user.is_staff = True
            changed = True
    
    if changed:
        user.save()


def _get_or_create_user_from_auth(identifier, auth_response, request, method='email'):
    """
    Standardized user creation/retrieval from Descope auth response.
    """
    user_id = auth_response.get('user', {}).get('userId')
    if not user_id:
        user_id = auth_response.get('sub')  # Fallback for Direct JWT responses
    
    # Try by descope_user_id
    try:
        user = User.objects.get(descope_user_id=user_id)
        if method == 'email':
            user.email = identifier
            user.is_verified = True
        else:
            user.phone_number = identifier
            user.is_phone_verified = True
        user.save()
        _merge_guest_data(user, request.META.get('HTTP_X_GUEST_ID'))
        _sync_roles_and_permissions(user, auth_response)
        return user, False
    except User.DoesNotExist:
        pass
        
    # Try by identifier
    try:
        if method == 'email':
            user = User.objects.get(email=identifier)
        else:
            user = User.objects.get(phone_number=identifier)
            
        user.descope_user_id = user_id
        if method == 'email':
            user.is_verified = True
        else:
            user.is_phone_verified = True
        user.save()
        _merge_guest_data(user, request.META.get('HTTP_X_GUEST_ID'))
        _sync_roles_and_permissions(user, auth_response)
        return user, False
    except User.DoesNotExist:
        pass
        
    # Create new user
    if method == 'email':
        username = identifier.split('@')[0]
        user = User.objects.create_user(
            username=username,
            email=identifier,
            descope_user_id=user_id,
            is_verified=True
        )
    else:
        username = f"user_{identifier.replace('+', '').replace('-', '')}"
        user = User.objects.create_user(
            username=username,
            phone_number=identifier,
            descope_user_id=user_id,
            is_phone_verified=True,
            is_verified=True
        )
        
    _merge_guest_data(user, request.META.get('HTTP_X_GUEST_ID'))
    _sync_roles_and_permissions(user, auth_response)
    return user, True


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def bootstrap_descope_roles(request):
    """
    Utility endpoint to pull all roles from Descope and create them as Django Groups.
    Requires Admin privileges.
    """
    try:
        descope_client = create_descope_client()
        # Using the MGMT SDK as per documentation provided
        resp = descope_client.mgmt.role.load_all()
        roles = resp.get('roles', [])
        
        created_groups = []
        for role in roles:
            group, created = Group.objects.get_or_create(
                name=role.get('name'),
                defaults={'name': role.get('name')}
            )
            if created:
                created_groups.append(role.get('name'))
        
        return Response({
            'message': f'Successfully synced {len(roles)} roles.',
            'created_groups': created_groups
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to bootstrap roles: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserRegistrationView(APIView):
    """Handle user registration using Descope"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                
                # Create user in Descope
                descope_user = descope_client.user.create(
                    login_id=serializer.validated_data['email'],
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password'],
                    name=f"{serializer.validated_data.get('first_name', '')} {serializer.validated_data.get('last_name', '')}".strip(),
                    phone=serializer.validated_data.get('phone_number', '')
                )
                
                # Create user in Django
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
                    'user': UserSerializer(user).data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}")
                return Response({
                    'error': 'Registration failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """Handle user login using Descope"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                
                # For password authentication, we'll use OTP-based approach
                # This is a passwordless system, so we'll redirect to OTP flow
                return Response({
                    'error': 'Password authentication not supported. Please use OTP authentication.',
                    'redirect_to_otp': True,
                    'message': 'Use /auth/otp/request/ endpoint for authentication'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                logger.error(f"Login failed: {str(e)}")
                return Response({
                    'error': 'Login failed',
                    'details': str(e)
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """Handle user logout"""
    
    def post(self, request):
        try:
            descope_client = create_descope_client()

            # Prefer refresh_token from request body
            refresh_token = None
            if isinstance(request.data, dict):
                refresh_token = request.data.get('refresh_token')

            # Fallback: Authorization header may carry a session token
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            session_token = None
            if auth_header.startswith('Bearer '):
                session_token = auth_header.split(' ', 1)[1]

            # Use refresh token for Descope logout when available
            if refresh_token:
                try:
                    descope_client.logout(refresh_token=refresh_token)
                except Exception as descope_err:
                    # Log but continue to deactivate locally
                    logger.warning(f"Descope logout with refresh token failed: {descope_err}")
                # Deactivate session locally
                UserSession.objects.filter(refresh_token=refresh_token).update(is_active=False)
            elif session_token:
                # If only session token is provided, deactivate locally
                UserSession.objects.filter(session_token=session_token).update(is_active=False)

            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return Response({'error': 'Logout failed', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    """Handle user profile retrieval and updates"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserProfileUpdateSerializer
        return UserSerializer


class PasswordResetView(APIView):
    """Handle password reset requests"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                
                # Password reset not supported in passwordless system
                return Response({
                    'error': 'Password reset not supported. Please use OTP authentication.',
                    'redirect_to_otp': True,
                    'message': 'Use /auth/otp/request/ endpoint for authentication'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                logger.error(f"Password reset failed: {str(e)}")
                return Response({
                    'error': 'Password reset failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Handle password reset confirmation"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                
                # Password update not supported in passwordless system
                return Response({
                    'error': 'Password update not supported. Please use OTP authentication.',
                    'redirect_to_otp': True,
                    'message': 'Use /auth/otp/request/ endpoint for authentication'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                logger.error(f"Password update failed: {str(e)}")
                return Response({
                    'error': 'Password update failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_sessions(request):
    """Get user's active sessions"""
    sessions = UserSession.objects.filter(user=request.user, is_active=True)
    return Response({
        'sessions': [
            {
                'id': session.id,
                'created_at': session.created_at,
                'expires_at': session.expires_at,
                'is_active': session.is_active
            }
            for session in sessions
        ]
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def revoke_session(request, session_id):
    """Revoke a specific session"""
    try:
        session = UserSession.objects.get(id=session_id, user=request.user)
        session.is_active = False
        session.save()
        
        return Response({
            'message': 'Session revoked successfully'
        }, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response({
            'error': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)


class PhoneOTPRequestView(APIView):
    """Handle phone OTP request using Descope"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PhoneOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = create_descope_client()
                phone_number = serializer.validated_data['phone_number']
                
                # Check if phone number is rate limited
                rate_limited = OTPAttempt.objects.filter(
                    identifier=phone_number,
                    attempt_type='phone',
                    created_at__gte=timezone.now() - timezone.timedelta(hours=1)
                ).count() >= 5
                
                if rate_limited:
                    return Response(
                        {'error': 'Too many OTP requests. Please try again later.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                
                # Fetch or create a single attempt tracker for this phone number
                attempt_rec, _ = OTPAttempt.objects.get_or_create(
                    identifier=phone_number,
                    attempt_type='phone',
                    defaults={'attempts_count': 0}
                )
                
                # If currently blocked, short-circuit
                if attempt_rec.is_blocked_now():
                    return Response(
                        {'error': 'Too many OTP requests. Please try again later.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                
                # Send OTP via Descope
                try:
                    auth_response = descope_client.otp.sign_up_or_in(
                        method=DeliveryMethod.SMS,
                        login_id=phone_number
                    )
                except Exception as descope_error:
                    logger.error(f"Descope OTP error: {str(descope_error)}")
                    return Response(
                        {'error': 'Failed to send verification code. Please try again later.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                
                # Store OTP attempt in database for tracking
                otp_record = PhoneOTP.objects.create(
                    phone_number=phone_number,
                    otp_code="****",  # We don't store actual OTP for security
                    expires_at=timezone.now() + timezone.timedelta(minutes=5)
                )
                
                # Track OTP attempt for rate limiting
                OTPAttempt.objects.create(
                    identifier=phone_number,
                    attempt_type='phone'
                )
                
                # Update attempt tracker for rate limiting
                attempt_rec.attempts_count += 1
                attempt_rec.last_attempt = timezone.now()
                # Block for an hour if more than 5 attempts in the last hour
                if attempt_rec.attempts_count >= 5:
                    attempt_rec.is_blocked = True
                    attempt_rec.blocked_until = timezone.now() + timezone.timedelta(hours=1)
                attempt_rec.save()
                
                return Response({
                    'message': 'Verification code sent successfully',
                    'phone_number': phone_number,
                    'expires_in': 300  # 5 minutes
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"OTP request failed: {str(e)}")
                return Response({
                    'error': 'Failed to send OTP',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PhoneOTPVerifyView(APIView):
    """Handle phone OTP verification using Descope"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                phone_number = serializer.validated_data['phone_number']
                otp_code = serializer.validated_data['otp_code']
                
                # Verify OTP with Descope
                auth_response = descope_client.otp.verify_code(
                    method=DeliveryMethod.SMS,
                    login_id=phone_number,
                    code=otp_code
                )
                
                if auth_response:
                    # Get or create user
                    user, created = self._get_or_create_user_from_phone(phone_number, auth_response)
                    
                    # Mark OTP as verified
                    PhoneOTP.objects.filter(
                        phone_number=phone_number,
                        is_verified=False
                    ).update(is_verified=True)
                    # Persist session
                    try:
                        session_jwt = auth_response[SESSION_TOKEN_NAME]["jwt"]
                        refresh_jwt = auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
                        UserSession.objects.update_or_create(
                            user=user,
                            session_token=session_jwt,
                            defaults={
                                'refresh_token': refresh_jwt,
                                'expires_at': timezone.now() + timedelta(days=30),
                                'is_active': True,
                            }
                        )
                    except Exception as persist_err:
                        logger.warning(f"Failed to persist session: {persist_err}")
                    
                    return Response({
                        'message': 'OTP verified successfully',
                        'user': UserSerializer(user).data,
                        'session_token': auth_response[SESSION_TOKEN_NAME]["jwt"],
                        'refresh_token': auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid OTP code'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"OTP verification failed: {str(e)}")
                return Response({
                    'error': 'OTP verification failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class PhoneLoginView(APIView):
    """Handle phone-based login with OTP"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                phone_number = serializer.validated_data['phone_number']
                otp_code = serializer.validated_data['otp_code']
                
                # Verify OTP and authenticate
                auth_response = descope_client.otp.verify_code(
                    method=DeliveryMethod.SMS,
                    login_id=phone_number,
                    code=otp_code
                )
                
                if auth_response:
                    # Get or create user
                    user, created = _get_or_create_user_from_auth(phone_number, auth_response, request, method='phone')
                    # Persist session
                    _persist_user_session(user, auth_response, request)
                    return Response({
                        'message': 'Login successful',
                        'user': UserSerializer(user).data,
                        'session_token': auth_response[SESSION_TOKEN_NAME]["jwt"],
                        'refresh_token': auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid OTP code'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                    
            except Exception as e:
                logger.error(f"Phone login failed: {str(e)}")
                return Response({
                    'error': 'Login failed',
                    'details': str(e)
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def phone_verification_status(request):
    """Check if user's phone is verified"""
    return Response({
        'is_phone_verified': request.user.is_phone_verified,
        'phone_number': request.user.phone_number
    })


class StaffLoginView(APIView):
    """OTP-based login for staff users (is_staff or is_superuser)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = StaffOtpLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data['method']
        identifier = serializer.validated_data['identifier']
        otp_code = serializer.validated_data['otp_code']
        device_id = serializer.validated_data.get('device_id')

        descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)

        try:
            delivery = DeliveryMethod.SMS if method == 'sms' else DeliveryMethod.EMAIL
            auth_response = descope_client.otp.verify_code(
                method=delivery,
                login_id=identifier,
                code=otp_code
            )

            if not auth_response:
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_401_UNAUTHORIZED)

            # Only allow existing staff/admin users
            from django.contrib.auth import get_user_model
            User = get_user_model()
            qs = User.objects.filter(
                (Q(email=identifier) | Q(phone_number=identifier)),
                is_active=True
            )
            try:
                user = qs.get()
            except User.DoesNotExist:
                # Just-in-time provision staff user if present in StaffDirectory
                try:
                    directory_entry = StaffDirectory.objects.get(identifier=identifier, is_active=True)
                except StaffDirectory.DoesNotExist:
                    return Response({'error': 'User not found or not permitted'}, status=status.HTTP_403_FORBIDDEN)

                # Determine username and fields based on identifier type
                username = identifier
                email = identifier if '@' in identifier else ''
                phone_number = '' if '@' in identifier else identifier
                first_name = ''
                last_name = ''
                if directory_entry.name:
                    parts = directory_entry.name.split(' ', 1)
                    first_name = parts[0]
                    last_name = parts[1] if len(parts) > 1 else ''

                # Create staff user (is_staff=True) without manual registration
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    is_active=True,
                    is_staff=True,
                )

            if not (user.is_staff or user.is_superuser):
                return Response({'error': 'Staff privileges required'}, status=status.HTTP_403_FORBIDDEN)

            # Persist session with metadata
            _persist_user_session(user, auth_response, request, device_id=device_id)

            return Response({
                'message': 'Staff login successful',
                'user': UserSerializer(user).data,
                'session_token': auth_response[SESSION_TOKEN_NAME]["jwt"],
                'refresh_token': auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Staff login failed: {str(e)}")
            return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class StaffPasswordLoginView(APIView):
    """Password-based login for staff users."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = StaffPasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data['identifier']
        password = serializer.validated_data['password']
        device_id = serializer.validated_data.get('device_id')

        user = authenticate(request, username=identifier, password=password)
        if not user:
            try:
                candidate = User.objects.get(email=identifier)
                user = authenticate(request, username=candidate.username, password=password)
            except User.DoesNotExist:
                user = None

        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        if not (user.is_staff or user.is_superuser):
            return Response({'error': 'Staff privileges required'}, status=status.HTTP_403_FORBIDDEN)

        token = uuid.uuid4().hex
        try:
            UserSession.objects.update_or_create(
                user=user,
                session_token=token,
                defaults={
                    'refresh_token': None,
                    'expires_at': timezone.now() + timedelta(days=30),
                    'is_active': True,
                    'device_id': device_id,
                    'user_agent': request.META.get('HTTP_USER_AGENT'),
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'last_activity': timezone.now(),
                }
            )
        except Exception as persist_err:
            logger.warning(f"Failed to persist password session: {persist_err}")

        return Response({
            'message': 'Staff password login successful',
            'user': UserSerializer(user).data,
            'session_token': token,
        }, status=status.HTTP_200_OK)


class AdminLoginView(APIView):
    """OTP-based login strictly for superusers."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = StaffOtpLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data['method']
        identifier = serializer.validated_data['identifier']
        otp_code = serializer.validated_data['otp_code']
        device_id = serializer.validated_data.get('device_id')

        descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)

        try:
            delivery = DeliveryMethod.SMS if method == 'sms' else DeliveryMethod.EMAIL
            auth_response = descope_client.otp.verify_code(
                method=delivery,
                login_id=identifier,
                code=otp_code
            )

            if not auth_response:
                return Response({'error': 'Invalid OTP code'}, status=status.HTTP_401_UNAUTHORIZED)

            from django.contrib.auth import get_user_model
            User = get_user_model()
            qs = User.objects.filter(
                (Q(email=identifier) | Q(phone_number=identifier)),
                is_active=True,
                is_superuser=True
            )
            try:
                user = qs.get()
            except User.DoesNotExist:
                return Response({'error': 'Admin privileges required'}, status=status.HTTP_403_FORBIDDEN)

            # Persist session with metadata
            _persist_user_session(user, auth_response, request, device_id=device_id)

            return Response({
                'message': 'Admin login successful',
                'user': UserSerializer(user).data,
                'session_token': auth_response[SESSION_TOKEN_NAME]["jwt"],
                'refresh_token': auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Admin login failed: {str(e)}")
            return Response({'error': 'Login failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class AdminPasswordLoginView(APIView):
    """Password-based login for admin (superuser)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = StaffPasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data['identifier']
        password = serializer.validated_data['password']
        device_id = serializer.validated_data.get('device_id')

        user = authenticate(request, username=identifier, password=password)
        if not user:
            try:
                candidate = User.objects.get(email=identifier)
                user = authenticate(request, username=candidate.username, password=password)
            except User.DoesNotExist:
                user = None

        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_superuser:
            return Response({'error': 'Admin privileges required'}, status=status.HTTP_403_FORBIDDEN)

        token = uuid.uuid4().hex
        try:
            UserSession.objects.update_or_create(
                user=user,
                session_token=token,
                defaults={
                    'refresh_token': None,
                    'expires_at': _get_session_expiry(),
                    'is_active': True,
                    'device_id': device_id,
                    'user_agent': request.META.get('HTTP_USER_AGENT'),
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'last_activity': timezone.now(),
                }
            )
        except Exception as persist_err:
            logger.warning(f"Failed to persist password session: {persist_err}")

        return Response({
            'message': 'Admin password login successful',
            'user': UserSerializer(user).data,
            'session_token': token,
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_phone_otp(request):
    """Resend OTP for phone verification"""
    phone_number = request.data.get('phone_number')
    
    if not phone_number:
        return Response({
            'error': 'Phone number is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
        
        # Send OTP via Descope
        auth_response = descope_client.otp.sign_up_or_in(
            method=DeliveryMethod.SMS,
            login_id=phone_number
        )
        
        # Update user's phone number if different
        if request.user.phone_number != phone_number:
            request.user.phone_number = phone_number
            request.user.save()
        
        return Response({
            'message': 'OTP resent successfully',
            'phone_number': phone_number
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Resend OTP failed: {str(e)}")
        return Response({
            'error': 'Failed to resend OTP',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


class EmailOTPRequestView(APIView):
    """Handle email OTP request using Descope"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EmailOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                
                # Check rate limiting
                if self._is_rate_limited(email, 'email'):
                    return Response({
                        'error': 'Too many OTP requests. Please try again later.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
                descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                
                # Send OTP via Descope
                try:
                    auth_response = descope_client.otp.sign_up_or_in(
                        method=DeliveryMethod.EMAIL,
                        login_id=email
                    )
                except Exception as descope_error:
                    logger.error(f"Descope Email OTP error: {str(descope_error)}")
                    return Response(
                        {'error': 'Failed to send verification code. Please try again later.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                
                # Store OTP attempt in database for tracking
                EmailOTP.objects.create(
                    email=email,
                    otp_code="****",  # We don't store actual OTP for security
                    expires_at=timezone.now() + timezone.timedelta(minutes=5)
                )
                
                # Update rate limiting
                self._update_rate_limit(email, 'email')
                
                return Response({
                    'message': 'Verification code sent successfully',
                    'email': email,
                    'expires_in': 300  # 5 minutes
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Email OTP request failed: {str(e)}")
                return Response({
                    'error': 'Failed to send OTP',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _is_rate_limited(self, identifier, method):
        """Check if identifier is rate limited"""
        try:
            attempt = OTPAttempt.objects.get(identifier=identifier, attempt_type=method)
            return attempt.is_blocked_now()
        except OTPAttempt.DoesNotExist:
            return False
    
    def _update_rate_limit(self, identifier, method):
        """Update rate limiting for identifier"""
        attempt, created = OTPAttempt.objects.get_or_create(
            identifier=identifier,
            attempt_type=method,
            defaults={'attempts_count': 0}
        )
        
        attempt.attempts_count += 1
        attempt.last_attempt = timezone.now()
        
        # Block if too many attempts
        if attempt.attempts_count >= 5:  # Max 5 attempts per hour
            attempt.is_blocked = True
            attempt.blocked_until = timezone.now() + timezone.timedelta(hours=1)
        
        attempt.save()


class EmailOTPVerifyView(APIView):
    """Handle email OTP verification using Descope"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EmailOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                otp_code = serializer.validated_data['otp_code']
                
                descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                
                # Verify OTP with Descope
                auth_response = descope_client.otp.verify_code(
                    method=DeliveryMethod.EMAIL,
                    login_id=email,
                    code=otp_code
                )
                
                if auth_response:
                    # Get or create user
                    user, created = _get_or_create_user_from_auth(email, auth_response, request, method='email')
                    
                    # Mark OTP as verified
                    EmailOTP.objects.filter(
                        email=email,
                        is_verified=False
                    ).update(is_verified=True)

                    # Persist session
                    _persist_user_session(user, auth_response, request)
                    
                    return Response({
                        'message': 'OTP verified successfully',
                        'user': UserSerializer(user).data,
                        'session_token': auth_response[SESSION_TOKEN_NAME]["jwt"],
                        'refresh_token': auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid OTP code'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Email OTP verification failed: {str(e)}")
                return Response({
                    'error': 'OTP verification failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
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
                
                descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                
                # Verify OTP and authenticate
                auth_response = descope_client.otp.verify_code(
                    method=DeliveryMethod.EMAIL,
                    login_id=email,
                    code=otp_code
                )
                
                if auth_response:
                    # Get or create user
                    user, created = _get_or_create_user_from_auth(email, auth_response, request, method='email')
                    # Persist session
                    _persist_user_session(user, auth_response, request)
                    
                    return Response({
                        'message': 'Login successful',
                        'user': UserSerializer(user).data,
                        'session_token': auth_response[SESSION_TOKEN_NAME]["jwt"],
                        'refresh_token': auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid OTP code'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                    
            except Exception as e:
                logger.error(f"Email login failed: {str(e)}")
                return Response({
                    'error': 'Login failed',
                    'details': str(e)
                }, status=status.HTTP_401_UNAUTHORIZED)
        
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
                
                # Check rate limiting
                if self._is_rate_limited(identifier, method):
                    return Response({
                        'error': 'Too many OTP requests. Please try again later.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
                descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                
                # Send OTP via Descope
                descope_method = DeliveryMethod.SMS if method == "phone" else DeliveryMethod.EMAIL
                auth_response = descope_client.otp.sign_up_or_in(
                    method=descope_method,
                    login_id=identifier
                )
                
                # Store OTP attempt in database for tracking
                if method == "phone":
                    PhoneOTP.objects.create(
                        phone_number=identifier,
                        otp_code="****",
                        expires_at=timezone.now() + timezone.timedelta(minutes=5)
                    )
                else:
                    EmailOTP.objects.create(
                        email=identifier,
                        otp_code="****",
                        expires_at=timezone.now() + timezone.timedelta(minutes=5)
                    )
                
                # Update rate limiting
                self._update_rate_limit(identifier, method)
                
                return Response({
                    'message': 'OTP sent successfully',
                    'identifier': identifier,
                    'method': method,
                    'expires_in': 300  # 5 minutes
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Unified OTP request failed: {str(e)}")
                return Response({
                    'error': 'Failed to send OTP',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _is_rate_limited(self, identifier, method):
        """Check if identifier is rate limited"""
        try:
            attempt = OTPAttempt.objects.get(identifier=identifier, attempt_type=method)
            return attempt.is_blocked_now()
        except OTPAttempt.DoesNotExist:
            return False
    
    def _update_rate_limit(self, identifier, method):
        """Update rate limiting for identifier"""
        attempt, created = OTPAttempt.objects.get_or_create(
            identifier=identifier,
            attempt_type=method,
            defaults={'attempts_count': 0}
        )
        
        attempt.attempts_count += 1
        attempt.last_attempt = timezone.now()
        
        # Block if too many attempts
        if attempt.attempts_count >= 5:  # Max 5 attempts per hour
            attempt.is_blocked = True
            attempt.blocked_until = timezone.now() + timezone.timedelta(hours=1)
        
        attempt.save()


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
                
                descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                
                # Verify OTP with Descope
                descope_method = DeliveryMethod.SMS if method == "phone" else DeliveryMethod.EMAIL
                auth_response = descope_client.otp.verify_code(
                    method=descope_method,
                    login_id=identifier,
                    code=otp_code
                )
                
                if auth_response:
                    # Get or create user
                    if method == "phone":
                        user, created = _get_or_create_user_from_auth(identifier, auth_response, request, method='phone')
                    else:
                        user, created = _get_or_create_user_from_auth(identifier, auth_response, request, method='email')
                    
                    # Mark OTP as verified
                    if method == "phone":
                        PhoneOTP.objects.filter(
                            phone_number=identifier,
                            is_verified=False
                        ).update(is_verified=True)
                    else:
                        EmailOTP.objects.filter(
                            email=identifier,
                            is_verified=False
                        ).update(is_verified=True)
                    
                    # Persist session with metadata
                    _persist_user_session(user, auth_response, request)
                    
                    return Response({
                        'message': 'OTP verified successfully',
                        'user': UserSerializer(user).data,
                        'session_token': auth_response[SESSION_TOKEN_NAME]["jwt"],
                        'refresh_token': auth_response[REFRESH_SESSION_TOKEN_NAME]["jwt"]
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid OTP code'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Unified OTP verification failed: {str(e)}")
                return Response({
                    'error': 'OTP verification failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class RefreshTokenView(APIView):
    """Handle token refresh using Descope refresh token"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            descope_client = create_descope_client()
            
            # Refresh session with Descope
            auth_response = descope_client.refresh_session(refresh_token)
            
            if not auth_response:
                return Response({'error': 'Token refresh failed'}, status=status.HTTP_401_UNAUTHORIZED)

            session_jwt = auth_response[SESSION_TOKEN_NAME]["jwt"]
            new_refresh_jwt = auth_response.get(REFRESH_SESSION_TOKEN_NAME, {}).get("jwt")
            
            # Update local session if refresh token changed
            if new_refresh_jwt:
                try:
                    UserSession.objects.filter(refresh_token=refresh_token).update(
                        session_token=session_jwt,
                        refresh_token=new_refresh_jwt,
                        expires_at=_get_session_expiry(),
                        last_activity=timezone.now()
                    )
                except Exception as e:
                    logger.warning(f"Failed to update session during refresh: {e}")
            else:
                # If refresh token not rotated, just update session token
                 try:
                    UserSession.objects.filter(refresh_token=refresh_token).update(
                        session_token=session_jwt,
                        last_activity=timezone.now(),
                        expires_at=_get_session_expiry(),
                    )
                 except Exception:
                     pass

            resp = {
                'session_token': session_jwt,
            }
            if new_refresh_jwt:
                resp['refresh_token'] = new_refresh_jwt
                
            return Response(resp, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return Response({'error': 'Token refresh failed', 'details': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

from rest_framework import viewsets

class UserAddressViewSet(viewsets.ModelViewSet):
    """ViewSet for UserAddress model"""
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # If this is set as default, unset other defaults
        if serializer.validated_data.get('is_default', False):
            UserAddress.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.validated_data.get('is_default', False):
            UserAddress.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save()

class ContactFormView(APIView):
    """View for submitting contact form messages"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Message sent successfully',
                'id': serializer.data['id']
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
