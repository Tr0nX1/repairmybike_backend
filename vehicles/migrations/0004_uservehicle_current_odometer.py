from django.db import migrations, models


def add_current_odometer_if_missing(apps, schema_editor):
    table_name = 'user_vehicles'
    column_name = 'current_odometer'
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            table_name,
        )
    }
    if column_name in existing_columns:
        return

    UserVehicle = apps.get_model('vehicles', 'UserVehicle')
    field = models.PositiveIntegerField(default=0)
    field.set_attributes_from_name(column_name)
    schema_editor.add_field(UserVehicle, field)


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0003_uservehicle'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_current_odometer_if_missing, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='uservehicle',
                    name='current_odometer',
                    field=models.PositiveIntegerField(default=0),
                ),
            ],
        ),
    ]
