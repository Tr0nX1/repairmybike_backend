from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from descope import DescopeClient
from django.conf import settings
import logging

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
