from django.core.management.base import BaseCommand
from decimal import Decimal

from services.models import Service, ServicePricing
from vehicles.models import VehicleModel


PRICE_LOOKUP = {
    # Engine Services
    "oil change": 600,
    "filter replacement": 200,
    "tune-up": 800,
    "engine repair/rebuild": 5000,

    # Electrical System
    "battery replacement": 1200,
    "headlamp replacement": 150,
    "tail light replacement": 120,
    "indicators repair/replacement": 100,
    "wiring check/repair": 300,
    "spark plugs replacement": 250,
    "stator replacement": 2000,

    # Brake System
    "brake pads replacement": 700,
    "brake fluid change": 400,
    "calipers service": 600,
    "rotors resurfacing/replacement": 1200,
    "brake lines inspection/replacement": 500,
    "drum brakes service": 600,

    # Suspension
    "fork oil change": 700,
    "shock absorbers replacement/service": 2500,
    "suspension inspection": 300,

    # Tires & Wheels
    "tire replacement": 1200,
    "wheel balancing": 150,
    "tire pressure check": 50,
    "wheel bearings replacement/service": 600,

    # Chain/Drive System
    "chain lubrication": 200,
    "sprocket replacement": 800,
    "drive belt replacement (scooters)": 1000,

    # Fuel System
    "carburetor cleaning/service": 800,
    "fuel filter replacement": 300,
    "fuel lines inspection/replacement": 200,
    "fuel tank cleaning/repair": 1000,

    # Cooling System
    "coolant check/replacement (liquid-cooled engines)": 400,

    # CVT Service
    "belt replacement": 1000,
    "clutch service": 1500,

    # Air Filter
    "air filter cleaning": 100,
    "air filter replacement": 250,

    # Body & Paint
    "body repair": 3000,
    "painting": 4000,

    # Clutch Service
    "clutch cable adjustment": 150,
    "clutch replacement": 1800,

    # Exhaust System
    "exhaust repair": 1000,
    "exhaust replacement": 3000,
    "exhaust gaskets replacement": 200,

    # General Inspection
    "safety check": 300,
    "diagnostic services": 500,
}


class Command(BaseCommand):
    help = (
        "Populate ServicePricing for all Service x VehicleModel combinations "
        "using a predefined default price table. Existing pricing rows are left intact."
    )

    def handle(self, *args, **options):
        vehicle_models = list(VehicleModel.objects.all())
        if not vehicle_models:
            self.stdout.write(self.style.WARNING("No vehicle models found. Populate vehicles first."))
            return

        created = 0
        for service in Service.objects.all():
            # lookup price; if not found, use fallback 500
            price_value = PRICE_LOOKUP.get(service.name.lower(), 500)
            for vm in vehicle_models:
                _, created_flag = ServicePricing.objects.get_or_create(
                    service=service,
                    vehicle_model=vm,
                    defaults={"price": Decimal(price_value)},
                )
                if created_flag:
                    created += 1
        self.stdout.write(self.style.SUCCESS(f"ServicePricing rows created: {created}"))