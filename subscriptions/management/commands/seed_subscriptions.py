from django.core.management.base import BaseCommand
from decimal import Decimal

from subscriptions.models import Plan


class Command(BaseCommand):
    help = "Seed sample subscription plans"

    def handle(self, *args, **options):
        # Define common services per tier
        basic_services = [
            "Brake adjustment and tightening",
            "Lubrication",
            "Screw tightening",
            "Chain adjustment and lubrication",
            "Air filter cleaning",
            "Engine oil (on MRP)",
        ]
        premium_services = [
            "Priority support",
            "Brake adjustment and tightening",
            "Lubrication",
            "Screw tightening",
            "Air filter cleaning",
            "Washing",
            "Polishing",
            "Engine oil (5% off on MRP)",
            "General bike inspection",
            "Chain lubrication and adjustment",
        ]

        def upsert_plan(slug, name, tier, price, period, visits, services, benefits):
            obj, created = Plan.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "tier": tier,
                    "description": f"{name} membership plan",
                    "benefits": benefits,
                    "services": services,
                    "price": Decimal(str(price)),
                    "currency": "INR",
                    "billing_period": period,
                    "included_visits": visits,
                    "active": True,
                },
            )
            if not created:
                obj.name = name
                obj.tier = tier
                obj.benefits = benefits
                obj.services = services
                obj.price = Decimal(str(price))
                obj.currency = "INR"
                obj.billing_period = period
                obj.included_visits = visits
                obj.active = True
                obj.save()
            return obj, created

        # Create Basic plans (3, 6, 12 months)
        bq, c_bq = upsert_plan(
            "basic-quarterly", "Basic Membership - Quarterly", "basic", 499, "quarterly", 1, basic_services,
            {"discounts": {"labour": 10}, "notes": "Max 1 service in 3 months"}
        )
        bh, c_bh = upsert_plan(
            "basic-half-yearly", "Basic Membership - Half Yearly", "basic", 899, "half_yearly", 3, basic_services,
            {"discounts": {"labour": 10}, "notes": "Max 3 services in 6 months"}
        )
        by, c_by = upsert_plan(
            "basic-yearly", "Basic Membership - Yearly", "basic", 1699, "yearly", 6, basic_services,
            {"discounts": {"labour": 10}, "notes": "Max 6 services in 12 months"}
        )

        # Create Premium plans (3, 6, 12 months)
        pq, c_pq = upsert_plan(
            "premium-quarterly", "Premium Membership - Quarterly", "premium", 699, "quarterly", 1, premium_services,
            {"discounts": {"labour": 15, "spare_parts": 10}, "priority_booking": True}
        )
        ph, c_ph = upsert_plan(
            "premium-half-yearly", "Premium Membership - Half Yearly", "premium", 1299, "half_yearly", 3, premium_services,
            {"discounts": {"labour": 15, "spare_parts": 10}, "priority_booking": True}
        )
        py, c_py = upsert_plan(
            "premium-yearly", "Premium Membership - Yearly", "premium", 2499, "yearly", 6, premium_services,
            {"discounts": {"labour": 15, "spare_parts": 10}, "priority_booking": True}
        )

        # Add a Quarterly plan with 3 visits included
        # Clean up deprecated sample plan
        Plan.objects.filter(slug="standard-quarterly").delete()

        # Legacy service population removed; all seeded plans define services explicitly above

        self.stdout.write(self.style.SUCCESS("Seeded subscription plans:"))
        for plan, created in [
            (bq, c_bq), (bh, c_bh), (by, c_by),
            (pq, c_pq), (ph, c_ph), (py, c_py),
        ]:
            self.stdout.write(self.style.SUCCESS(
                f"- {plan.name} | period={plan.billing_period} | price={plan.price} {plan.currency} | visits={plan.included_visits} | created={bool(created)}"
            ))
            if isinstance(plan.services, list) and plan.services:
                self.stdout.write(self.style.SUCCESS("  services:"))
                for s in plan.services:
                    self.stdout.write(self.style.SUCCESS(f"    • {s}"))