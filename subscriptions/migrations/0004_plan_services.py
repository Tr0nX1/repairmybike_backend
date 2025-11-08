from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0003_subscription_contact_phone_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='services',
            field=models.JSONField(blank=True, default=list),
        ),
    ]