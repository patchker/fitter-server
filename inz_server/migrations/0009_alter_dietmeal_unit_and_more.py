# Generated by Django 4.2.5 on 2023-11-12 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0008_ingredient_measurementunit_meal_fish_free_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dietmeal',
            name='unit',
            field=models.CharField(choices=[('g', 'Grams'), ('pcs', 'Pieces')], default='g', max_length=3),
        ),
        migrations.AlterField(
            model_name='ingredient',
            name='measurement_unit',
            field=models.CharField(choices=[('g', 'Grams'), ('pcs', 'Pieces')], default='g', max_length=3),
        ),
        migrations.DeleteModel(
            name='MeasurementUnit',
        ),
    ]