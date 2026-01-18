from rest_framework import permissions

class IsGuestOrAuthenticated(permissions.BasePermission):
    """
    Allow access if the user is a registered user OR a guest user with a valid Guest ID.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user:
            return False
            
        # Registered user
        if user.is_authenticated:
            return True
            
        # Identified guest user
        if getattr(user, 'is_guest', False):
            return True
            
        return False


class IsGuestOnly(permissions.BasePermission):
    """
    Allow access ONLY to guest users.
    """
    def has_permission(self, request, view):
        user = request.user
        return user and not user.is_authenticated and getattr(user, 'is_guest', False)


class IsAuthenticatedOnly(permissions.BasePermission):
    """
    Strictly require a registered user (not a guest).
    This is effectively the same as permissions.IsAuthenticated, 
    but explicit for our Guest architecture.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
