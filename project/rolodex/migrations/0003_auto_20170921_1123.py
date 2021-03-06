# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-21 01:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('rolodex', '0002_auto_20170919_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='email',
            name='created_at',
            field=models.DateField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='email',
            name='last_checked_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='phone',
            name='created_at',
            field=models.DateField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='phone',
            name='last_checked_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
