# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-09-17 06:27
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0002_navigation'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='navigation',
            options={'ordering': ['order']},
        ),
    ]
