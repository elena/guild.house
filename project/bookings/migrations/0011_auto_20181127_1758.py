# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-27 06:58
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0010_auto_20181127_1231'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='is_confirmed',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='booking',
            name='party_size',
            field=models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(100), django.core.validators.MinValueValidator(1)], verbose_name='Number of people'),
        ),
    ]
