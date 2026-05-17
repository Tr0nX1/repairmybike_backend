from django.db import migrations


def ensure_static_content_table(apps, schema_editor):
    StaticContent = apps.get_model('content', 'StaticContent')
    table_name = StaticContent._meta.db_table
    existing_tables = schema_editor.connection.introspection.table_names()

    if table_name not in existing_tables:
        schema_editor.create_model(StaticContent)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(ensure_static_content_table, migrations.RunPython.noop),
    ]
