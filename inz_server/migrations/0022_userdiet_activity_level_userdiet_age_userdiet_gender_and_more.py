# Generated by Django 4.2.5 on 2024-01-22 16:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0021_remove_meal_fish_free_remove_meal_gluten_free_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdiet',
            name='activity_level',
            field=models.CharField(default='medium', max_length=50),
        ),
        migrations.AddField(
            model_name='userdiet',
            name='age',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userdiet',
            name='gender',
            field=models.CharField(default='male', max_length=50),
        ),
        migrations.AddField(
            model_name='userdiet',
            name='height',
            field=models.IntegerField(default=0),
        ),
    ]
