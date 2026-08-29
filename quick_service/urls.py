from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import QuickServiceConfigView, QuickServiceRequestViewSet

router = DefaultRouter()
router.register(r'requests', QuickServiceRequestViewSet, basename='quick-service-request')

urlpatterns = [
    path('config/', QuickServiceConfigView.as_view(), name='quick-service-config'),
    path('', include(router.urls)),
]
