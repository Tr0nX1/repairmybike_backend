from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_alter_customer_internal_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='total_spent',
            field=models.DecimalField(
                max_digits=10,
                decimal_places=2,
                default=0
            ),
        ),
    ]
