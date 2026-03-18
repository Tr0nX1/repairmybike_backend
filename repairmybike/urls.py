from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .health import health_check, readiness_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('dashboard/', include('dashboard.urls')),
    path('health/', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),
    path('api/auth/', include('authentication.urls')),
    path('api/vehicles/', include('vehicles.urls')),
    path('api/services/', include('services.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/staff/', include('staff.urls')),
    path('api/shop/', include('shop.urls')),
    path('api/spare-parts/', include('spare_parts.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/content/', include('content.urls')),
    path('api/quick-service/', include('quick_service.urls')),
    path('api/feedback/', include('feedback.urls')),
    path('api/notifications/', include('notifications.urls')),
]

# Serve media files in development and production (fallback)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
