from django.core.management.base import BaseCommand
from services.models import ServiceCategory, Service

SERVICES_MAP = {
    "Engine Services": [
        ("Oil change", "Replace old engine oil with manufacturer-recommended grade"),
        ("Filter replacement", "Replace oil and fuel filters to ensure clean operation"),
        ("Tune-up", "Comprehensive engine tune-up for optimal performance"),
        ("Engine repair/rebuild", "Partial or full engine overhaul and repair"),
    ],
    "Electrical System": [
        ("Battery replacement", "Test and replace motorcycle battery if required"),
        ("Headlamp replacement", "Install new headlamp bulb or assembly"),
        ("Tail light replacement", "Replace rear tail light bulb or unit"),
        ("Indicators repair/replacement", "Fix or replace turn indicators and relay"),
        ("Wiring check/repair", "Inspect and repair electrical wiring issues"),
        ("Spark plugs replacement", "Replace worn or fouled spark plugs"),
        ("Stator replacement", "Replace faulty stator for charging system"),
    ],
    "Brake System": [
        "Brake pads replacement",
        "Brake fluid change",
        "Calipers service",
        "Rotors resurfacing/replacement",
        "Brake lines inspection/replacement",
        "Drum brakes service",
    ],
    "Suspension": [
        "Fork oil change",
        "Shock absorbers replacement/service",
        "Suspension inspection",
    ],
    "Tires & Wheels": [
        "Tire replacement",
        "Wheel balancing",
        "Tire pressure check",
        "Wheel bearings replacement/service",
    ],
    "Chain/Drive System": [
        "Chain lubrication",
        "Sprocket replacement",
        "Drive belt replacement (scooters)",
    ],
    "Fuel System": [
        "Carburetor cleaning/service",
        "Fuel filter replacement",
        "Fuel lines inspection/replacement",
        "Fuel tank cleaning/repair",
    ],
    "Cooling System": [
        "Coolant check/replacement (liquid-cooled engines)",
    ],
    "CVT Service": [
        "Belt replacement",
        "Clutch service",
    ],
    "Air Filter": [
        "Air filter cleaning",
        "Air filter replacement",
    ],
    "Body & Paint": [
        "Body repair",
        "Painting",
    ],
    "Clutch Service": [
        "Clutch cable adjustment",
        "Clutch replacement",
    ],
    "Exhaust System": [
        "Exhaust repair",
        "Exhaust replacement",
        "Exhaust gaskets replacement",
    ],
    "General Inspection": [
        "Safety check",
        "Diagnostic services",
    ],
}


class Command(BaseCommand):
    help = "Load services under major service categories. Ensure categories exist first (use load_service_categories)."

    def handle(self, *args, **options):
        total_created = 0
        for category_name, services in SERVICES_MAP.items():
            category, _ = ServiceCategory.objects.get_or_create(name=category_name)
            for service_item in services:
                if isinstance(service_item, tuple):
                    service_name, description = service_item
                else:
                    service_name = service_item
                    description = ""
                service, created = Service.objects.get_or_create(
                    service_category=category,
                    name=service_name,
                    defaults={"description": description}
                )
                if created:
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(f"Created service: {service_name} under {category_name}"))
        self.stdout.write(self.style.SUCCESS(f"Done. Total new services: {total_created}"))