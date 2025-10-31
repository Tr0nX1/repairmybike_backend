from django.core.management.base import BaseCommand
from vehicles.models import VehicleType, VehicleBrand, VehicleModel

# Scooter brands and their models
SCOOTER_DATA = {
    "HERO": [
        "Honda Street 100",
        "Honda Pleasure",
        "Maestro",
        "Duet",
        "Pleasure Plus",
        "Destini 125",
        "Maestro Edge 110",
        "Maestro Edge 125",
        "Xoom 110",
    ],
    "BAJAJ": [
        "Chetak (2 Stroke)",
    ],
    "TVS": [
        "Scooty",
        "Scooty Pep",
        "Wego",
        "Streak",
        "Jupiter",
        "Scooty Pep Plus",
        "Zest 110",
        "Jupiter 125",
        "Ntorq 125",
    ],
    "HONDA": [
        "Activa 3G",
        "Activa 4G",
        "Activa 5G",
        "Activa 6G",
        "Activa 125",
        "Dio",
        "Aviator",
        "Cliq",
        "Grazia",
    ],
    "SUZUKI": [
        "Access 125",
    ],
    "YAMAHA": [
        "Fascino 125",
        "Ray ZR 125",
        "Alpha",
    ],
    "MAHINDRA": [
        "Rodeo",
        "Gusto",
        "Duro",
        "Flyte",
    ],
}


class Command(BaseCommand):
    help = "Load scooter vehicle brands and models into the database."

    def handle(self, *args, **options):
        vehicle_type, _ = VehicleType.objects.get_or_create(name="Scooter")

        created_brands = 0
        created_models = 0

        for brand_name, model_list in SCOOTER_DATA.items():
            brand, brand_created = VehicleBrand.objects.get_or_create(
                vehicle_type=vehicle_type, name=brand_name
            )
            if brand_created:
                created_brands += 1
                self.stdout.write(self.style.SUCCESS(f"Created brand: {brand_name}"))
            for model_name in model_list:
                model, model_created = VehicleModel.objects.get_or_create(
                    vehicle_brand=brand, name=model_name
                )
                if model_created:
                    created_models += 1
                    self.stdout.write(self.style.SUCCESS(f"  Added model: {model_name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Brands created: {created_brands}, Models created: {created_models}."
            )
        )