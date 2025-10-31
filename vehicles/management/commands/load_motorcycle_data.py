from django.core.management.base import BaseCommand, CommandError
from vehicles.models import VehicleType, VehicleBrand, VehicleModel

data = {
    "HERO MOTOCOP": [
        "Splendor Plus",
        "HF Deluxe",
        "Hero Passion Xtec",
        "Hero Passion Plus",
        "Super Splendor",
        "CD 100",
        "Honda Sleek",
        "CBZ",
        "Honda Hunk",
        "Impulse",
        "Achiever 150",
        "Glamour FI",
        "Xpulse 200 4V",
        "Xpulse 200T 4V",
    ],
    "TVS": [
        "Max 100",
        "Center",
        "Fiero 150",
        "TVS Star",
        "Victor",
        "Apache 150",
        "Apache 160",
        "Flame 125",
        "Phoenix 125",
        "Suzuki Samurai",
        "Suzuki Shogun",
        "Suzuki Shaolin",
        "TVS Sports",
        "Radeon",
        "Star City Plus",
        "Apache RTR 160",
        "Apache RTR 160 4V",
        "Apache RTR 180",
        "Apache RTR 200 4V",
        "Apache RR 310",
    ],
    "BAJAJ": [
        "Boxer",
        "Caliber",
        "Kawasaki 45",
        "Wind 125",
        "Discover 100",
        "Discover 125",
        "Pulsar 150 DTSI",
        "Pulsar 220 DTS-Fi",
        "XCD 125",
        "Platina 100",
        "Platina 110 ABS",
        "CT 110X",
        "Pulsar NS 125",
        "Pulsar NS 150",
        "Pulsar N 160",
        "Pulsar NS 160",
        "Pulsar NS 200",
        "Pulsar RS 200",
        "Dominar 250",
        "Dominar 400",
        "Avenger Street 160",
        "Avenger Cruise 220",
    ],
}


class Command(BaseCommand):
    help = "Load motorcycle vehicle brands and models into the database."

    def handle(self, *args, **options):
        # Ensure vehicle type exists
        vehicle_type, _ = VehicleType.objects.get_or_create(name="Motor Cycle")

        created_brands = 0
        created_models = 0

        for brand_name, models in data.items():
            brand, brand_created = VehicleBrand.objects.get_or_create(
                vehicle_type=vehicle_type, name=brand_name
            )
            if brand_created:
                created_brands += 1
                self.stdout.write(self.style.SUCCESS(f"Created brand: {brand_name}"))
            for model_name in models:
                model, model_created = VehicleModel.objects.get_or_create(
                    vehicle_brand=brand,
                    name=model_name,
                )
                if model_created:
                    created_models += 1
                    self.stdout.write(self.style.SUCCESS(f"  Added model: {model_name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Brands created: {created_brands}, Models created: {created_models}."
            )
        )