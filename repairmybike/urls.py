from django.contrib import admin
from django.urls import path, include
from .health import health_check, readiness_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),
    path('api/auth/', include('authentication.urls')),
    path('api/vehicles/', include('vehicles.urls')),
    path('api/services/', include('services.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/staff/', include('staff.urls')),
    path('api/shop/', include('shop.urls')),
]