# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-09-29 14:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0019_auto_20180930_0003'),
    ]

    operations = [
        migrations.AddField(
            model_name='copy',
            name='checked_at',
            field=models.DateField(blank=True, null=True),
        ),
    ]
