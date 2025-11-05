from django.core.management.base import BaseCommand
from decimal import Decimal

from vehicles.models import VehicleType, VehicleBrand, VehicleModel
from spare_parts.models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartFitment,
    SparePartImage,
)
from django.core.files.base import ContentFile
import urllib.request
import base64

PNG_PLACEHOLDER_BASE64 = (
    # 1x1 pixel PNG (black)
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlJwXQAAAAASUVORK5CYII="
)


def _attach_image(part: SparePart, url: str, filename: str, is_primary: bool = False, alt_text: str = ""):
    try:
        # Skip if an identical filename already exists for this part
        if part.images.filter(image=f"spare_parts/images/{filename}").exists():
            return
        data = None
        try:
            data = urllib.request.urlopen(url, timeout=6).read()
        except Exception:
            # Fallback to an embedded PNG if network is unavailable
            data = base64.b64decode(PNG_PLACEHOLDER_BASE64)
        img = SparePartImage(spare_part=part, is_primary=is_primary, alt_text=alt_text)
        img.image.save(filename, ContentFile(data), save=True)
    except Exception as e:
        # Non-fatal: continue seeding other items
        print(f"⚠ Failed to attach image for {part.sku}: {e}")


def _set_category_image(category: SparePartCategory, url: str, filename: str):
    try:
        if category.image and category.image.name:
            return
        data = None
        try:
            data = urllib.request.urlopen(url, timeout=6).read()
        except Exception:
            data = base64.b64decode(PNG_PLACEHOLDER_BASE64)
        category.image.save(filename, ContentFile(data), save=True)
    except Exception as e:
        print(f"⚠ Failed to set image for category {category.slug}: {e}")


class Command(BaseCommand):
    help = "Seed spare parts catalog with images and complete fields"

    def handle(self, *args, **options):
        # Ensure vehicle types/brands/models exist
        vt_scooter, _ = VehicleType.objects.get_or_create(name="Scooter")
        vt_motorcycle, _ = VehicleType.objects.get_or_create(name="Motor Cycle")

        honda, _ = VehicleBrand.objects.get_or_create(vehicle_type=vt_scooter, name="HONDA")
        hero, _ = VehicleBrand.objects.get_or_create(vehicle_type=vt_motorcycle, name="HERO MOTOCOP")

        activa_125, _ = VehicleModel.objects.get_or_create(vehicle_brand=honda, name="Activa 125")
        splendor_plus, _ = VehicleModel.objects.get_or_create(vehicle_brand=hero, name="Splendor Plus")

        # Catalog base: categories + brands
        categories = [
            {"name": "Battery", "slug": "battery", "description": "Two-wheeler batteries", "image_text": "Battery"},
            {"name": "Engine Oil", "slug": "engine-oil", "description": "Premium motorcycle engine oil", "image_text": "Engine+Oil"},
            {"name": "Brake Pads", "slug": "brake-pads", "description": "Front and rear brake pads", "image_text": "Brake+Pads"},
            {"name": "Air Filter", "slug": "air-filter", "description": "OEM and performance air filters", "image_text": "Air+Filter"},
            {"name": "Spark Plug", "slug": "spark-plug", "description": "High-performance spark plugs", "image_text": "Spark+Plug"},
            {"name": "Chain & Sprocket", "slug": "chain-sprocket", "description": "Chain and sprocket kits", "image_text": "Chain+Sprocket"},
            {"name": "Tyre", "slug": "tyre", "description": "Two-wheeler tyres", "image_text": "Tyre"},
        ]

        cat_objs = {}
        for c in categories:
            obj, _ = SparePartCategory.objects.get_or_create(
                name=c["name"], defaults={"slug": c["slug"], "description": c["description"]}
            )
            _set_category_image(obj, f"https://via.placeholder.com/800x600.png?text={c['image_text']}", f"cat_{c['slug']}.png")
            cat_objs[c["slug"]] = obj

        brand_names = ["Amaron", "Exide", "Motul", "Castrol", "Bosch", "TVS", "NGK", "RK", "MRF", "K&N"]
        brand_objs = {}
        for b in brand_names:
            obj, _ = SparePartBrand.objects.get_or_create(name=b, defaults={"slug": b.lower()})
            brand_objs[b] = obj

        # Sample products (10 items across categories)
        amaron_btz4, created1 = SparePart.objects.get_or_create(
            sku="AP-BTZ4",
            defaults={
                "category": cat_objs["battery"],
                "brand": brand_objs["Amaron"],
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
            },
        )

        # Attach images (PNG placeholders) if none exist
        if amaron_btz4.images.count() == 0:
            _attach_image(
                amaron_btz4,
                url="https://via.placeholder.com/800x600.png?text=Amaron+Battery",
                filename="amaron_battery_primary.png",
                is_primary=True,
                alt_text="Amaron Battery",
            )
            _attach_image(
                amaron_btz4,
                url="https://via.placeholder.com/800x600.png?text=Amaron+Battery+Side",
                filename="amaron_battery_side.png",
                is_primary=False,
                alt_text="Amaron Battery side view",
            )

        exide_xplore, created2 = SparePart.objects.get_or_create(
            sku="EX-XP-4AH",
            defaults={
                "category": cat_objs["battery"],
                "brand": brand_objs["Exide"],
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
            },
        )

        if exide_xplore.images.count() == 0:
            _attach_image(
                exide_xplore,
                url="https://via.placeholder.com/800x600.png?text=Exide+Battery",
                filename="exide_battery_primary.png",
                is_primary=True,
                alt_text="Exide Battery",
            )
            _attach_image(
                exide_xplore,
                url="https://via.placeholder.com/800x600.png?text=Exide+Battery+Box",
                filename="exide_battery_box.png",
                is_primary=False,
                alt_text="Exide battery packaging",
            )

        # Fitments for a few parts (guarded lookups to avoid undefined references)
        try:
            SparePartFitment.objects.get_or_create(spare_part=amaron_btz4, vehicle_model=activa_125, defaults={"notes": "Scooter fitment"})
            SparePartFitment.objects.get_or_create(spare_part=exide_xplore, vehicle_model=activa_125, defaults={"notes": "Scooter fitment"})
            SparePartFitment.objects.get_or_create(spare_part=amaron_btz4, vehicle_model=splendor_plus, defaults={"notes": "Motorcycle fitment"})
            bosch = SparePart.objects.filter(slug="bosch-front-brake-pads").first()
            if bosch:
                SparePartFitment.objects.get_or_create(spare_part=bosch, vehicle_model=splendor_plus, defaults={"notes": "Front pads"})
            ngk = SparePart.objects.filter(slug="ngk-cr7-spark-plug").first()
            if ngk:
                SparePartFitment.objects.get_or_create(spare_part=ngk, vehicle_model=splendor_plus, defaults={"notes": "Standard plug"})
        except Exception as e:
            print(f"⚠ Fitment seeding encountered an issue: {e}")

        total_parts = SparePart.objects.count()
        self.stdout.write(self.style.SUCCESS("Seeded categories, brands, spare parts, images, and fitments."))
        self.stdout.write(self.style.SUCCESS(f"  Categories: {', '.join([c['name'] for c in categories])}"))
        self.stdout.write(self.style.SUCCESS(f"  Brands: {', '.join(brand_names)}"))
        self.stdout.write(self.style.SUCCESS(f"  Total parts: {total_parts} (idempotent creation)"))
        # Engine Oil
        motul_7100_10w40, _ = SparePart.objects.get_or_create(
            sku="MOT-7100-10W40-1L",
            defaults={
                "category": cat_objs["engine-oil"],
                "brand": brand_objs["Motul"],
                "name": "Motul 7100 4T 10W40 1L",
                "slug": "motul-7100-10w40-1l",
                "short_description": "Fully synthetic 4T engine oil for motorcycles",
                "description": "High-performance fully synthetic oil ensuring superior engine protection.",
                "specs": {"viscosity": "10W40", "type": "Fully Synthetic", "volume_ml": 1000},
                "warranty_months_total": 0,
                "mrp": Decimal("950.00"),
                "sale_price": Decimal("899.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 30,
            },
        )
        if motul_7100_10w40.images.count() == 0:
            _attach_image(
                motul_7100_10w40,
                url="https://via.placeholder.com/800x600.png?text=Motul+7100",
                filename="motul_7100.png",
                is_primary=True,
                alt_text="Motul 7100 10W40",
            )

        castrol_power1, _ = SparePart.objects.get_or_create(
            sku="CAS-PWR1-10W50-1L",
            defaults={
                "category": cat_objs["engine-oil"],
                "brand": brand_objs["Castrol"],
                "name": "Castrol POWER1 10W50 1L",
                "slug": "castrol-power1-10w50-1l",
                "short_description": "Synthetic technology bike engine oil",
                "description": "Optimized for acceleration with excellent wear protection.",
                "specs": {"viscosity": "10W50", "type": "Synthetic", "volume_ml": 1000},
                "warranty_months_total": 0,
                "mrp": Decimal("880.00"),
                "sale_price": Decimal("829.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 25,
            },
        )
        if castrol_power1.images.count() == 0:
            _attach_image(
                castrol_power1,
                url="https://via.placeholder.com/800x600.png?text=Castrol+Power1",
                filename="castrol_power1.png",
                is_primary=True,
                alt_text="Castrol POWER1",
            )

        # Brake Pads
        bosch_brake_front, _ = SparePart.objects.get_or_create(
            sku="BOS-BRK-FRT-STD",
            defaults={
                "category": cat_objs["brake-pads"],
                "brand": brand_objs["Bosch"],
                "name": "Bosch Front Brake Pads (Std)",
                "slug": "bosch-front-brake-pads",
                "short_description": "Reliable stopping power front pads",
                "description": "OEM-quality front brake pads for popular commuter bikes.",
                "specs": {"position": "Front", "compound": "Organic", "compatibility": "Commuter bikes"},
                "warranty_months_total": 6,
                "mrp": Decimal("700.00"),
                "sale_price": Decimal("649.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 40,
            },
        )
        if bosch_brake_front.images.count() == 0:
            _attach_image(bosch_brake_front, "https://via.placeholder.com/800x600.png?text=Brake+Pads", "bosch_brake_front.png", True, "Bosch Brake Pads")

        # Air Filter
        tvs_air_filter, _ = SparePart.objects.get_or_create(
            sku="TVS-AIR-STD",
            defaults={
                "category": cat_objs["air-filter"],
                "brand": brand_objs["TVS"],
                "name": "TVS OEM Air Filter",
                "slug": "tvs-oem-air-filter",
                "short_description": "OEM-grade replacement air filter",
                "description": "High filtration efficiency for longer engine life.",
                "specs": {"type": "Paper", "micron": 20},
                "warranty_months_total": 6,
                "mrp": Decimal("320.00"),
                "sale_price": Decimal("299.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 50,
            },
        )
        if tvs_air_filter.images.count() == 0:
            _attach_image(tvs_air_filter, "https://via.placeholder.com/800x600.png?text=Air+Filter", "tvs_air_filter.png", True, "TVS Air Filter")

        # Spark Plug
        ngk_cr7, _ = SparePart.objects.get_or_create(
            sku="NGK-CR7",
            defaults={
                "category": cat_objs["spark-plug"],
                "brand": brand_objs["NGK"],
                "name": "NGK CR7 Spark Plug",
                "slug": "ngk-cr7-spark-plug",
                "short_description": "Copper core spark plug for reliable ignition",
                "description": "Engineered for consistent performance and longevity.",
                "specs": {"thread": "M10", "heat_range": "7"},
                "warranty_months_total": 12,
                "mrp": Decimal("220.00"),
                "sale_price": Decimal("199.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 100,
            },
        )
        if ngk_cr7.images.count() == 0:
            _attach_image(ngk_cr7, "https://via.placeholder.com/800x600.png?text=Spark+Plug", "ngk_cr7.png", True, "NGK CR7 Spark Plug")

        # Chain & Sprocket kit
        rk_chain_kit, _ = SparePart.objects.get_or_create(
            sku="RK-CHAIN-KIT-428",
            defaults={
                "category": cat_objs["chain-sprocket"],
                "brand": brand_objs["RK"],
                "name": "RK 428 Chain & Sprocket Kit",
                "slug": "rk-428-chain-sprocket-kit",
                "short_description": "Durable chain and sprocket set",
                "description": "High-strength chain with precision-cut sprockets for smooth power delivery.",
                "specs": {"chain_pitch": "428", "teeth_front": 14, "teeth_rear": 42},
                "warranty_months_total": 12,
                "mrp": Decimal("2400.00"),
                "sale_price": Decimal("2199.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 12,
            },
        )
        if rk_chain_kit.images.count() == 0:
            _attach_image(rk_chain_kit, "https://via.placeholder.com/800x600.png?text=Chain+%26+Sprocket", "rk_chain_kit.png", True, "RK Chain Kit")

        # Performance Air Filter
        kn_high_flow, _ = SparePart.objects.get_or_create(
            sku="KN-HF-AF-01",
            defaults={
                "category": cat_objs["air-filter"],
                "brand": brand_objs["K&N"],
                "name": "K&N High-Flow Air Filter",
                "slug": "kn-high-flow-air-filter",
                "short_description": "Washable reusable performance air filter",
                "description": "Improves airflow and offers long service life.",
                "specs": {"type": "Cotton gauze", "washable": True},
                "warranty_months_total": 12,
                "mrp": Decimal("3200.00"),
                "sale_price": Decimal("2990.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 10,
            },
        )
        if kn_high_flow.images.count() == 0:
            _attach_image(kn_high_flow, "https://via.placeholder.com/800x600.png?text=K%26N+Air+Filter", "kn_air_filter.png", True, "K&N High-Flow Air Filter")

        # Tyre
        mrf_zapper, _ = SparePart.objects.get_or_create(
            sku="MRF-ZAPPER-90-90-12",
            defaults={
                "category": cat_objs.setdefault("tyre", SparePartCategory.objects.get_or_create(name="Tyre", defaults={"slug": "tyre", "description": "Two-wheeler tyres"})[0]),
                "brand": brand_objs["MRF"],
                "name": "MRF Zapper 90/90-12",
                "slug": "mrf-zapper-90-90-12",
                "short_description": "Tubeless scooter tyre 90/90-12",
                "description": "Excellent grip and durability for city riding.",
                "specs": {"size": "90/90-12", "type": "Tubeless"},
                "warranty_months_total": 36,
                "mrp": Decimal("2700.00"),
                "sale_price": Decimal("2499.00"),
                "currency": "INR",
                "in_stock": True,
                "stock_qty": 18,
            },
        )
        if mrf_zapper.images.count() == 0:
            _attach_image(mrf_zapper, "https://via.placeholder.com/800x600.png?text=MRF+Tyre", "mrf_zapper.png", True, "MRF Zapper Tyre")