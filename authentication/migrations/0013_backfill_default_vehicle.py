from django.db import migrations


def backfill_default_vehicle(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    UserVehicle = apps.get_model('vehicles', 'UserVehicle')

    default_user_vehicles = (
        UserVehicle.objects
        .filter(is_default=True)
        .order_by('user_id', '-updated_at', '-created_at')
    )

    seen_user_ids = set()
    for user_vehicle in default_user_vehicles:
        if user_vehicle.user_id in seen_user_ids:
            continue
        seen_user_ids.add(user_vehicle.user_id)
        User.objects.filter(
            id=user_vehicle.user_id,
            default_vehicle__isnull=True,
        ).update(default_vehicle_id=user_vehicle.vehicle_model_id)


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0012_user_is_manager'),
        ('vehicles', '0003_uservehicle'),
    ]

    operations = [
        migrations.RunPython(backfill_default_vehicle, migrations.RunPython.noop),
    ]
