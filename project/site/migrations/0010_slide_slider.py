# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-09-26 00:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0009_auto_20180926_0938'),
    ]

    operations = [
        migrations.AddField(
            model_name='slide',
            name='slider',
            field=models.CharField(choices=[('home', 'home'), ('games', 'games')], default='home', max_length=32),
            preserve_default=False,
        ),
    ]
