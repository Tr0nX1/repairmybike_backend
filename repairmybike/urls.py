from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .health import health_check, readiness_check

# Import ViewSets for API Aliases
from bookings.views import BookingViewSet
from authentication.views import StaffDirectoryViewSet

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),

    # --- API Aliases (Backward Compatibility) ---
    # Flutter expects /api/bookings/ instead of /api/bookings/bookings/
    path('api/bookings/', BookingViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='bookings-base-alias'),
    path('api/bookings/<int:pk>/', BookingViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='bookings-detail-alias'),
    
    # Custom actions for Booking alias (parity with bookings.urls)
    path('api/bookings/<int:pk>/approve-parts/', BookingViewSet.as_view({'post': 'approve_parts'}), name='bookings-approve-parts-alias'),
    path('api/bookings/<int:pk>/reject-parts/', BookingViewSet.as_view({'post': 'reject_parts'}), name='bookings-reject-parts-alias'),
    path('api/bookings/<int:pk>/cancel/', BookingViewSet.as_view({'post': 'cancel'}), name='bookings-cancel-alias'),

    # Next.js expects /api/auth/staff/ instead of /api/auth/staff-directory/
    path('api/auth/staff/', StaffDirectoryViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='staff-auth-alias'),
    path('api/auth/staff/<int:pk>/', StaffDirectoryViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='staff-auth-detail-alias'),

    # --- Standard App Routes ---
    path('api/auth/', include('authentication.urls')),
    path('api/vehicles/', include('vehicles.urls')),
    path('api/services/', include('services.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/staff/', include('staff.urls')),
    path('api/shop/', include('shop.urls')),
    path('api/spare-parts/', include('spare_parts.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/cms/', include('cms.urls')),
    path('api/content/', include('content.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/feedback/', include('bookings.urls_feedback')),
]

# Serve media files in development and production (fallback)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
