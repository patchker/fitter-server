# Generated by Django 4.2.5 on 2023-11-09 13:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inz_server', '0005_zamowienie_userdiet'),
    ]

    operations = [
        migrations.RenameField(
            model_name='zamowienie',
            old_name='userdiet',
            new_name='user_diet',
        ),
    ]
