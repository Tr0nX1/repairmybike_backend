from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from descope import DescopeClient
from django.conf import settings
from django.utils import timezone
import logging
from .models import UserSession

logger = logging.getLogger(__name__)
User = get_user_model()
JWT_LEEWAY_SECONDS = 30


class DescopeAuthentication(BaseAuthentication):
    """
    Custom authentication class for Descope integration with lazy initialization.
    Handles development mode where credentials may not be available.
    """
    
    _descope_client = None
    _client_initialized = False
    _client_failed = False
    
    @classmethod
    def _get_descope_client(cls):
        """
        Lazily initialize Descope client on first use.
        Returns None if credentials are not available (development mode).
        """
        if cls._client_failed:
            return None
        
        if cls._client_initialized and cls._descope_client:
            return cls._descope_client
        
        try:
            project_id = settings.DESCOPE_PROJECT_ID
            management_key = settings.DESCOPE_MANAGEMENT_KEY
            
            # Allow development mode without Descope credentials
            if not project_id or not management_key:
                logger.warning("Descope credentials not configured - Descope authentication disabled")
                cls._client_failed = True
                return None
            
            cls._descope_client = DescopeClient(
                project_id=project_id,
                management_key=management_key,
                jwt_validation_leeway=JWT_LEEWAY_SECONDS
            )
            cls._client_initialized = True
            logger.info("Descope client initialized successfully")
            return cls._descope_client
        except Exception as e:
            logger.error(f"Failed to initialize Descope client: {str(e)}")
            cls._client_failed = True
            return None
    
    def authenticate(self, request):
        """
        Authenticate user using Descope session token.
        Returns None if no auth header (allows other authenticators).
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return None
            
        try:
            # Extract token from "Bearer <token>" format
            if not auth_header.startswith('Bearer '):
                return None
                
            token = auth_header.split(' ')[1]
            
            # Get Descope client (lazy initialization)
            descope_client = self._get_descope_client()
            
            if not descope_client:
                logger.warning("Descope authentication requested but client not available")
                return None
            
            # Validate token with Descope
            jwt_response = descope_client.validate_session(token)
            
            if not jwt_response:
                return None
                
            # Extract user info from JWT
            user_id = jwt_response.get('sub')
            if not user_id:
                return None
                
            # Get or create user
            user, created = self._get_or_create_user(jwt_response)
            
            if created:
                logger.info(f"Created new user: {user.email}")
            else:
                logger.info(f"Authenticated existing user: {user.email}")
                
            return (user, token)
            
        except Exception as e:
            logger.error(f"Descope authentication failed: {str(e)}")
            return None
    
    def _get_or_create_user(self, jwt_response):
        """
        Get or create user based on Descope JWT response
        """
        user_id = jwt_response.get('sub')
        email = jwt_response.get('email')
        name = jwt_response.get('name', '')
        phone_number = jwt_response.get('phone_number', '')
        profile_picture = jwt_response.get('picture', '')
        
        # Try to get user by descope_user_id first
        try:
            user = User.objects.get(descope_user_id=user_id)
            # Update user info if needed
            if email and user.email != email:
                user.email = email
            if name and user.first_name != name.split(' ')[0]:
                user.first_name = name.split(' ')[0]
            if len(name.split(' ')) > 1 and user.last_name != name.split(' ')[1]:
                user.last_name = name.split(' ')[1]
            if phone_number and user.phone_number != phone_number:
                user.phone_number = phone_number
            if profile_picture and user.profile_picture != profile_picture:
                user.profile_picture = profile_picture
            user.save()
            return user, False
        except User.DoesNotExist:
            pass
        
        # Try to get user by email
        if email:
            try:
                user = User.objects.get(email=email)
                user.descope_user_id = user_id
                user.save()
                return user, False
            except User.DoesNotExist:
                pass
        
        # Create new user
        username = email or f"user_{user_id[:8]}"
        user = User.objects.create_user(
            username=username,
            email=email,
            descope_user_id=user_id,
            first_name=name.split(' ')[0] if name else '',
            last_name=name.split(' ')[1] if len(name.split(' ')) > 1 else '',
            phone_number=phone_number,
            profile_picture=profile_picture,
            is_verified=True  # Descope handles verification
        )
        
        return user, True


class DescopeSessionAuthentication(BaseAuthentication):
    """
    Alternative authentication using Descope session tokens
    """
    
    def authenticate(self, request):
        """
        Authenticate using session token from cookies or headers
        """
        session_token = request.COOKIES.get('DS') or request.META.get('HTTP_X_SESSION_TOKEN')
        
        if not session_token:
            return None
            
        try:
            from descope import DescopeClient
            descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
            
            # Validate session token
            jwt_response = descope_client.validate_session(session_token)
            
            if not jwt_response:
                return None
                
            user_id = jwt_response.get('sub')
            if not user_id:
                return None
                
            # Get user
            try:
                user = User.objects.get(descope_user_id=user_id)
                return (user, session_token)
            except User.DoesNotExist:
                return None
                
        except Exception as e:
            logger.error(f"Session authentication failed: {str(e)}")
            return None


class PasswordSessionAuthentication(BaseAuthentication):
    """
    Password-based session authentication using locally stored UserSession.
    Accepts token from Authorization header (Bearer) or X-Session-Token header.
    """

    def authenticate(self, request):
        # Extract token
        token = None
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
        if not token:
            token = request.META.get('HTTP_X_SESSION_TOKEN')

        if not token:
            return None

        try:
            # Look up an active, non-expired session
            session = UserSession.objects.filter(
                session_token=token,
                is_active=True,
                expires_at__gt=timezone.now(),
            ).select_related('user').first()

            if not session:
                return None

            user = session.user
            if not user.is_active:
                return None

            return (user, token)

        except Exception as e:
            logger.error(f"PasswordSessionAuthentication failed: {e}")
            return None


class GuestUser(AnonymousUser):
    """Custom AnonymousUser that carries a Guest ID"""
    def __init__(self, guest_id):
        self.guest_id = guest_id
        super().__init__()

    @property
    def is_authenticated(self):
        return False

    @property
    def is_guest(self):
        return True


class GuestAuthentication(BaseAuthentication):
    """
    Identifies Guest users via X-Guest-ID header.
    Does NOT provide full 'authenticated' status, but allows tracking.
    """
    def authenticate(self, request):
        guest_id = request.META.get('HTTP_X_GUEST_ID')
        if not guest_id:
            return None
        
        # We don't necessarily need to hit the DB here if we just trust the UUID,
        # but for Blinkit-style, we might want to ensure the session exists.
        from .models import GuestSession
        try:
            # Validate UUID format
            import uuid
            uuid_obj = uuid.UUID(guest_id)
            
            # Use get_or_create to ensure session exists in DB
            guest_session, _ = GuestSession.objects.get_or_create(guest_id=uuid_obj)
            return (GuestUser(guest_id=str(guest_session.guest_id)), None)
        except Exception:
            return None
