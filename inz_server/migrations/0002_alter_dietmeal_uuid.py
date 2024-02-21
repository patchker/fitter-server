# Generated by Django 4.2.5 on 2023-11-02 21:48

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dietmeal',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]