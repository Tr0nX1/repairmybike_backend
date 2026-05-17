from django.apps import AppConfig


class SparePartsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'spare_parts'

    def ready(self):
        import spare_parts.signals
    verbose_name = "Spare Parts"