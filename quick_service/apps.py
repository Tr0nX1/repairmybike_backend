from django.apps import AppConfig


class QuickServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quick_service'

    def ready(self):
        import quick_service.signals
