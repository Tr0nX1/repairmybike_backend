from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Seed all demo data (vehicles, services, pricing, subscriptions, spare parts) with one command."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-static",
            action="store_true",
            help="Also run collectstatic after seeding",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting full data seed..."))

        # Database migrations first to ensure tables exist
        self.stdout.write("Applying migrations...")
        call_command("migrate", interactive=False)

        # Vehicles
        self.stdout.write("Loading vehicle data (motorcycle + scooter)...")
        call_command("load_motorcycle_data")
        call_command("load_scooter_data")

        # Services and pricing
        self.stdout.write("Loading service categories and services...")
        call_command("load_service_categories")
        call_command("load_major_services")
        self.stdout.write("Loading default service pricing...")
        call_command("load_default_service_pricing")

        # Subscriptions
        self.stdout.write("Seeding subscriptions...")
        call_command("seed_subscriptions")

        # Spare parts catalog (+ images)
        self.stdout.write("Seeding spare parts catalog...")
        call_command("seed_spare_parts")

        # Optionally collect static files
        if options.get("with_static"):
            self.stdout.write("Collecting static files...")
            call_command("collectstatic", interactive=False, verbosity=0)

        self.stdout.write(self.style.SUCCESS("All data seeded successfully."))