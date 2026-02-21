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
    Custom authentication class for Descope integration
    """
    
    def __init__(self):
        self.descope_client = DescopeClient(
            project_id=settings.DESCOPE_PROJECT_ID,
            management_key=settings.DESCOPE_MANAGEMENT_KEY,
            jwt_validation_leeway=JWT_LEEWAY_SECONDS
        )
    
    def authenticate(self, request):
        """
        Authenticate user using Descope session token
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return None
            
        try:
            # Extract token from "Bearer <token>" format
            if not auth_header.startswith('Bearer '):
                return None
                
            token = auth_header.split(' ')[1]
            
            # Validate token with Descope
            jwt_response = self.descope_client.validate_session(token)
            
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
            logger.error(f"Authentication failed: {str(e)}")
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
        
        # Split name into first and last name
        name_parts = name.split(' ') if name else []
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Try to get user by descope_user_id first
        try:
            user = User.objects.get(descope_user_id=user_id)
            # Update user info if needed
            changed = False
            if email and user.email != email:
                user.email = email
                changed = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                changed = True
            if phone_number and user.phone_number != phone_number:
                user.phone_number = phone_number
                changed = True
            if profile_picture and user.profile_picture != profile_picture:
                user.profile_picture = profile_picture
                changed = True
            
            if changed:
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
            first_name=first_name,
            last_name=last_name,
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
