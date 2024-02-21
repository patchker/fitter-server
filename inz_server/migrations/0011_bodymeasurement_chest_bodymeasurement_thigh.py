# Generated by Django 4.2.5 on 2023-11-20 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0010_exercise_alter_dietmeal_unit_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bodymeasurement',
            name='chest',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='bodymeasurement',
            name='thigh',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
