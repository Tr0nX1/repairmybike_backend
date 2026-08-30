from django.apps import AppConfig


class QuickServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quick_service'

    def ready(self):
        # Import signals to register receivers
        from . import signals  # noqa: F401
