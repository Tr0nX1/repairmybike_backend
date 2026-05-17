from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0005_booking_discount_amount_booking_odometer_reading'),
    ]

    operations = [
        # Already handled by 0004 - this is a no-op to maintain migration history
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='customer',
                    name='internal_notes',
                    field=models.TextField(blank=True, default=''),
                ),
            ],
            database_operations=[]
        ),
    ]
