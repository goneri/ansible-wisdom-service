# Generated by Django 4.2.11 on 2024-07-02 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_user_organization_fix_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="telemetry_opt_out",
            field=models.BooleanField(db_column="telemetry_opt_out", default=False),
        ),
    ]