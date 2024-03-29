# Generated by Django 4.2.5 on 2023-12-28 12:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0019_alter_emailverificationtoken_expires_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dietmeal',
            name='unit',
            field=models.CharField(choices=[('g', 'Grams'), ('szt', 'Sztuki'), ('ml', 'Milliliters')], default='g', max_length=3),
        ),
        migrations.AlterField(
            model_name='ingredient',
            name='measurement_unit',
            field=models.CharField(choices=[('g', 'Grams'), ('szt', 'Sztuki'), ('ml', 'Milliliters')], default='g', max_length=3),
        ),
    ]
