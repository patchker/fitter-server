# Generated by Django 4.2.5 on 2023-11-25 20:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0012_alter_trainingsession_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='Exercise2',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
        ),
    ]
