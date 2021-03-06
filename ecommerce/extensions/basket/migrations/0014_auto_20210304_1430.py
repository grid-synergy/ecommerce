# Generated by Django 2.2.15 on 2021-03-04 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0013_auto_20200305_1448'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basket',
            name='status',
            field=models.CharField(choices=[('Open', 'Open - currently active'), ('Merged', 'Merged - superceded by another basket'), ('Saved', 'Saved - for items to be purchased later'), ('Frozen', 'Frozen - the basket cannot be modified'), ('Submitted', 'Submitted - has been ordered at the checkout'), ('Commited', 'Commited - has been commited')], default='Open', max_length=128, verbose_name='Status'),
        ),
    ]
