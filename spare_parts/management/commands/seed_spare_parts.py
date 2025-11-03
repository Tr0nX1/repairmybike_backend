from django.core.management.base import BaseCommand
from decimal import Decimal

from vehicles.models import VehicleType, VehicleBrand, VehicleModel
from spare_parts.models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartFitment,
)


class Command(BaseCommand):
    help = "Seed sample spare parts (batteries) and vehicle fitments"

    def handle(self, *args, **options):
        # Ensure vehicle types/brands/models exist
        vt_scooter, _ = VehicleType.objects.get_or_create(name="Scooter")
        vt_motorcycle, _ = VehicleType.objects.get_or_create(name="Motor Cycle")

        honda, _ = VehicleBrand.objects.get_or_create(vehicle_type=vt_scooter, name="HONDA")
        hero, _ = VehicleBrand.objects.get_or_create(vehicle_type=vt_motorcycle, name="HERO MOTOCOP")

        activa_125, _ = VehicleModel.objects.get_or_create(vehicle_brand=honda, name="Activa 125")
        splendor_plus, _ = VehicleModel.objects.get_or_create(vehicle_brand=hero, name="Splendor Plus")

        # Catalog base: category + brands
        battery_cat, _ = SparePartCategory.objects.get_or_create(
            name="Battery",
            defaults={"slug": "battery", "description": "Two-wheeler batteries"},
        )

        amaron_brand, _ = SparePartBrand.objects.get_or_create(name="Amaron", defaults={"slug": "amaron"})
        exide_brand, _ = SparePartBrand.objects.get_or_create(name="Exide", defaults={"slug": "exide"})

        # Sample products
        amaron_btz4, created1 = SparePart.objects.get_or_create(
            sku="AP-BTZ4",
            defaults={
                "category": battery_cat,
                "brand": amaron_brand,
                "name": "Amaron AP-BTZ4 4Ah VRLA",
                "slug": "amaron-ap-btz4-4ah",
                "short_description": "4Ah VRLA, zero-maintenance, high cranking power",
                "description": "Amaron Pro Bike Rider series with VRLA technology, spill-proof and durable.",
                "specs": {
                    "capacity_ah": 4,
                    "voltage_v": 12,
                    "technology": "VRLA",
                    "maintenance": "Zero-maintenance",
                    "cranking_power": "High",
                },
                "warranty_months_total": 48,
                "warranty_free_months": 24,
                "warranty_pro_rata_months": 24,
                "mrp": Decimal("3200.00"),
                "sale_price": Decimal("2999.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 20,
                "active": True,
            },
        )

        exide_xplore, created2 = SparePart.objects.get_or_create(
            sku="EX-XP-4AH",
            defaults={
                "category": battery_cat,
                "brand": exide_brand,
                "name": "Exide Xplore 4Ah VRLA",
                "slug": "exide-xplore-4ah",
                "short_description": "Factory-charged VRLA, zero-maintenance",
                "description": "Exide Xplore with Calcium Effects Technology, built for Indian road conditions.",
                "specs": {
                    "capacity_ah": 4,
                    "voltage_v": 12,
                    "technology": "VRLA",
                    "maintenance": "Zero-maintenance",
                },
                "warranty_months_total": 48,
                "warranty_free_months": 24,
                "warranty_pro_rata_months": 24,
                "mrp": Decimal("3100.00"),
                "sale_price": Decimal("2899.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 15,
                "active": True,
            },
        )

        # Fitments
        SparePartFitment.objects.get_or_create(spare_part=amaron_btz4, vehicle_model=activa_125, defaults={"notes": "Scooter fitment"})
        SparePartFitment.objects.get_or_create(spare_part=exide_xplore, vehicle_model=activa_125, defaults={"notes": "Scooter fitment"})
        SparePartFitment.objects.get_or_create(spare_part=amaron_btz4, vehicle_model=splendor_plus, defaults={"notes": "Motorcycle fitment"})

        self.stdout.write(self.style.SUCCESS("Seeded spare parts and fitments:"))
        self.stdout.write(self.style.SUCCESS(f"  Category: {battery_cat.name}"))
        self.stdout.write(self.style.SUCCESS(f"  Brands: {amaron_brand.name}, {exide_brand.name}"))
        self.stdout.write(self.style.SUCCESS(f"  Parts created: {int(created1)} + {int(created2)} (may be 0 if existed)"))
        self.stdout.write(self.style.SUCCESS("  Fitments: Activa 125, Splendor Plus linked."))