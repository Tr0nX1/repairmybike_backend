import uuid
import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from descope import DescopeClient, DeliveryMethod, SESSION_TOKEN_NAME, REFRESH_SESSION_TOKEN_NAME
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    UserProfileUpdateSerializer, PhoneOTPRequestSerializer,
    PhoneOTPVerifySerializer, PhoneLoginSerializer,
    EmailOTPRequestSerializer, EmailOTPVerifySerializer, EmailLoginSerializer,
    UnifiedOTPRequestSerializer, UnifiedOTPVerifySerializer
)
from .models import UserSession, PhoneOTP, EmailOTP, OTPAttempt
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
    
    def _get_or_create_user(self, auth_response):
        """Get or create user based on Descope auth response"""
        user_id = auth_response.get('user', {}).get('userId')
        email = auth_response.get('user', {}).get('email')
        name = auth_response.get('user', {}).get('name', '')
        
        try:
            user = User.objects.get(descope_user_id=user_id)
            return user, False
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=email,
                email=email,
                descope_user_id=user_id,
                first_name=name.split(' ')[0] if name else '',
                last_name=name.split(' ')[1] if len(name.split(' ')) > 1 else '',
                is_verified=True
            )
            return user, True


class UserLogoutView(APIView):
    """Handle user logout"""
    
    def post(self, request):
        try:
            # Get session token from request
            session_token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
            
            if session_token:
                descope_client = create_descope_client()
                descope_client.logout(refresh_token=session_token)
                
                # Deactivate session in Django
                UserSession.objects.filter(session_token=session_token).update(is_active=False)
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return Response({
                'error': 'Logout failed',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    """Handle user profile retrieval and updates"""
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
    
    def _get_or_create_user_from_phone(self, phone_number, auth_response):
        """Get or create user based on phone number and Descope response"""
        user_id = auth_response.get('user', {}).get('userId')
        
        try:
            # Try to get user by descope_user_id
            user = User.objects.get(descope_user_id=user_id)
            user.phone_number = phone_number
            user.is_phone_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        try:
            # Try to get user by phone number
            user = User.objects.get(phone_number=phone_number)
            user.descope_user_id = user_id
            user.is_phone_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = f"user_{phone_number.replace('+', '').replace('-', '')}"
        user = User.objects.create_user(
            username=username,
            phone_number=phone_number,
            descope_user_id=user_id,
            is_phone_verified=True,
            is_verified=True
        )
        
        return user, True


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
                    user, created = self._get_or_create_user_from_phone(phone_number, auth_response)
                    
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
    
    def _get_or_create_user_from_phone(self, phone_number, auth_response):
        """Get or create user based on phone number and Descope response"""
        user_id = auth_response.get('user', {}).get('userId')
        
        try:
            user = User.objects.get(descope_user_id=user_id)
            user.phone_number = phone_number
            user.is_phone_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        try:
            user = User.objects.get(phone_number=phone_number)
            user.descope_user_id = user_id
            user.is_phone_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = f"user_{phone_number.replace('+', '').replace('-', '')}"
        user = User.objects.create_user(
            username=username,
            phone_number=phone_number,
            descope_user_id=user_id,
            is_phone_verified=True,
            is_verified=True
        )
        
        return user, True


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def phone_verification_status(request):
    """Check if user's phone is verified"""
    return Response({
        'is_phone_verified': request.user.is_phone_verified,
        'phone_number': request.user.phone_number
    })


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
                    user, created = self._get_or_create_user_from_email(email, auth_response)
                    
                    # Mark OTP as verified
                    EmailOTP.objects.filter(
                        email=email,
                        is_verified=False
                    ).update(is_verified=True)
                    
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
    
    def _get_or_create_user_from_email(self, email, auth_response):
        """Get or create user based on email and Descope response"""
        user_id = auth_response.get('user', {}).get('userId')
        
        try:
            # Try to get user by descope_user_id
            user = User.objects.get(descope_user_id=user_id)
            user.email = email
            user.is_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        try:
            # Try to get user by email
            user = User.objects.get(email=email)
            user.descope_user_id = user_id
            user.is_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = email.split('@')[0]
        user = User.objects.create_user(
            username=username,
            email=email,
            descope_user_id=user_id,
            is_verified=True
        )
        
        return user, True


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
                    user, created = self._get_or_create_user_from_email(email, auth_response)
                    
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
    
    def _get_or_create_user_from_email(self, email, auth_response):
        """Get or create user based on email and Descope response"""
        user_id = auth_response.get('user', {}).get('userId')
        
        try:
            user = User.objects.get(descope_user_id=user_id)
            user.email = email
            user.is_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        try:
            user = User.objects.get(email=email)
            user.descope_user_id = user_id
            user.is_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = email.split('@')[0]
        user = User.objects.create_user(
            username=username,
            email=email,
            descope_user_id=user_id,
            is_verified=True
        )
        
        return user, True


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
                        user, created = self._get_or_create_user_from_phone(identifier, auth_response)
                    else:
                        user, created = self._get_or_create_user_from_email(identifier, auth_response)
                    
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
    
    def _get_or_create_user_from_phone(self, phone_number, auth_response):
        """Get or create user based on phone number and Descope response"""
        user_id = auth_response.get('user', {}).get('userId')
        
        try:
            user = User.objects.get(descope_user_id=user_id)
            user.phone_number = phone_number
            user.is_phone_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        try:
            user = User.objects.get(phone_number=phone_number)
            user.descope_user_id = user_id
            user.is_phone_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = f"user_{phone_number.replace('+', '').replace('-', '')}"
        user = User.objects.create_user(
            username=username,
            phone_number=phone_number,
            descope_user_id=user_id,
            is_phone_verified=True,
            is_verified=True
        )
        
        return user, True
    
    def _get_or_create_user_from_email(self, email, auth_response):
        """Get or create user based on email and Descope response"""
        user_id = auth_response.get('user', {}).get('userId')
        
        try:
            user = User.objects.get(descope_user_id=user_id)
            user.email = email
            user.is_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        try:
            user = User.objects.get(email=email)
            user.descope_user_id = user_id
            user.is_verified = True
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        # Create new user
        username = email.split('@')[0]
        user = User.objects.create_user(
            username=username,
            email=email,
            descope_user_id=user_id,
            is_verified=True
        )
        
        return user, True
