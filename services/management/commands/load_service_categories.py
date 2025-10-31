from django.core.management.base import BaseCommand
from services.models import ServiceCategory

CATEGORIES = {
    "Engine Services": "Oil change, filter replacement, tune-up, engine repair/rebuild",
    "Electrical System": "Battery, headlamp, tail light, indicators, wiring, spark plugs, stator",
    "Brake System": "Brake pads, brake fluid, calipers, rotors, brake lines, drum brakes",
    "Suspension": "Fork oil, shock absorbers, inspection",
    "Tires & Wheels": "Replacement, balancing, pressure check, wheel bearings",
    "Chain/Drive System": "Chain lubrication, sprocket replacement, drive belt (for scooters)",
    "Fuel System": "Carburetor cleaning, fuel filter, fuel lines, fuel tank",
    "Cooling System": "Coolant check/replacement (for liquid-cooled engines)",
    "CVT Service": "Belt replacement, clutch service (Scooter specific)",
    "Air Filter": "Cleaning or replacement",
    "Body & Paint": "Repair and painting",
    "Clutch Service": "Cable adjustment, clutch replacement",
    "Exhaust System": "Repair, replacement, gaskets",
    "General Inspection": "Safety check, diagnostic services",
}


class Command(BaseCommand):
    help = "Load major service categories into the database."

    def handle(self, *args, **options):
        created = 0
        for name, description in CATEGORIES.items():
            obj, obj_created = ServiceCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            if obj_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {name}"))
        self.stdout.write(self.style.SUCCESS(f"Done. Total new categories: {created}"))