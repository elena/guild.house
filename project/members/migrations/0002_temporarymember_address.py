# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-19 05:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='temporarymember',
            name='address',
            field=models.TextField(blank=True, default=''),
        ),
    ]