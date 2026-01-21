from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Setup default Groups and Permissions for Staff and Admin roles'

    def handle(self, *args, **options):
        # 1. Create Groups
        staff_group, _ = Group.objects.get_or_create(name='Staff')
        admin_group, _ = Group.objects.get_or_create(name='Admin')

        # 2. Define permission mappings
        # (app_label, model_name, [perms])
        # Perms: 'view', 'add', 'change', 'delete'
        
        staff_perms = [
            # Bookings
            ('bookings', 'booking', ['view', 'change']),
            ('bookings', 'bookingservice', ['view', 'change']),
            ('bookings', 'customer', ['view', 'change']),
            
            # Spare Parts / Orders
            ('spare_parts', 'order', ['view', 'change']),
            ('spare_parts', 'orderitem', ['view', 'change']),
            ('spare_parts', 'sparepart', ['view', 'change']),
            ('spare_parts', 'sparepartfitment', ['view', 'change']),
            ('spare_parts', 'sparepartcategory', ['view']),
            ('spare_parts', 'sparepartbrand', ['view']),
            
            # Services (Read-only for staff)
            ('services', 'service', ['view']),
            ('services', 'servicecategory', ['view']),
            ('services', 'servicepricing', ['view']),
            
            # Vehicles
            ('vehicles', 'vehiclebrand', ['view']),
            ('vehicles', 'vehiclemodel', ['view']),
            ('vehicles', 'vehicletype', ['view']),

            # Payments (Read-only context)
            ('payments', 'payment', ['view']),
            
            # Subscriptions
            ('subscriptions', 'plan', ['view']),
            ('subscriptions', 'subscription', ['view']),
        ]

        # Admin gets everything (handled by is_superuser usually, but we'll populate the group)
        # For this script, we'll give Admin all 'view', 'add', 'change', 'delete' for core apps
        admin_apps = ['bookings', 'spare_parts', 'services', 'vehicles', 'payments', 'subscriptions', 'authentication', 'shop']

        self.stdout.write("Setting up Staff permissions...")
        self._assign_permissions(staff_group, staff_perms)

        self.stdout.write("Setting up Admin permissions (Full Access)...")
        self._assign_all_permissions(admin_group, admin_apps)

        self.stdout.write(self.style.SUCCESS('Successfully configured Groups and Permissions.'))

    def _assign_permissions(self, group, mapping):
        group.permissions.clear()
        for app_label, model_name, perms in mapping:
            for perm_type in perms:
                codename = f"{perm_type}_{model_name}"
                try:
                    permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permission not found: {app_label}.{codename}"))

    def _assign_all_permissions(self, group, apps):
        for app in apps:
            permissions = Permission.objects.filter(content_type__app_label=app)
            group.permissions.add(*permissions)
