# Generated by Django 4.2.5 on 2023-11-20 21:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0011_bodymeasurement_chest_bodymeasurement_thigh'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingsession',
            name='date',
            field=models.DateTimeField(),
        ),
    ]
