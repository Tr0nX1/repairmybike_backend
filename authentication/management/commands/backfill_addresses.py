from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import User, UserAddress
from bookings.models import Booking
from spare_parts.models import Order
import json

class Command(BaseCommand):
    help = 'Backfills legacy user address strings into the distinct UserAddress model architecture.'

    def handle(self, *args, **options):
        users = User.objects.all()
        created_count = 0
        skipped_count = 0

        self.stdout.write(self.style.NOTICE(f"Starting data backfill evaluation for {users.count()} users..."))

        for user in users:
            # 1. Skip if they already have an address
            if user.addresses.exists():
                skipped_count += 1
                continue

            # 2. They don't have an address. We need to find their most recent Booking or Spare Parts Order
            # Since User might not have a direct ForeignKey in legacy bookings, we match by phone
            phone = user.phone_number
            if not phone:
                continue

            last_booking = Booking.objects.filter(customer__phone=phone, address__isnull=False).exclude(address='').order_by('-created_at').first()
            last_order = Order.objects.filter(phone=phone, address__isnull=False).exclude(address='').order_by('-created_at').first()

            target_source = None
            if last_booking and last_order:
                # Compare timestamps
                if last_booking.created_at > last_order.created_at:
                    target_source = last_booking
                else:
                    target_source = last_order
            elif last_booking:
                target_source = last_booking
            elif last_order:
                target_source = last_order

            if not target_source:
                continue

            # 3. Extract legacy data
            address_str = getattr(target_source, 'address', "") or ""
            address_details = getattr(target_source, 'address_details', {}) or {}

            # Fallback Parsing Logic if JSON structured data is missing
            flat = address_details.get('flat_house_no') or address_details.get('flatHouseNo')
            area = address_details.get('area_street') or address_details.get('areaStreet')
            landmark = address_details.get('landmark', '')
            pincode = address_details.get('pincode', '')
            city = address_details.get('town_city') or address_details.get('townCity', 'Unknown')
            state = address_details.get('state', 'Unknown')

            name = getattr(target_source, 'customer_name', None)
            if not name and hasattr(target_source, 'customer'):
                name = target_source.customer.name
            if not name:
                name = user.get_full_name() or "Customer"

            # If the address details were entirely empty, try to salvage the raw string
            if not flat and not area and address_str:
                parts = [p.strip() for p in address_str.split(',') if p.strip()]
                if len(parts) >= 1:
                    flat = parts[0]
                if len(parts) >= 2:
                    area = parts[1]
                if len(parts) >= 3:
                    city = parts[len(parts) - 2] if len(parts) > 3 else parts[2]

            if not flat:
                flat = "N/A"
            if not area:
                area = address_str if address_str else "N/A"

            with transaction.atomic():
                UserAddress.objects.create(
                    user=user,
                    full_name=name,
                    phone_number=phone,
                    flat_house_no=flat,
                    area_street=area,
                    landmark=landmark,
                    pincode=pincode,
                    town_city=city,
                    state=state,
                    is_default=True
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f">> Migrated legacy address for User: {phone}"))

        self.stdout.write(self.style.SUCCESS(f"\nBackfill Complete! Migrated {created_count} orphaned records. Skipped {skipped_count} users who already possessed structured data."))
