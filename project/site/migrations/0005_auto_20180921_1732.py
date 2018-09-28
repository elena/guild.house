# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-09-21 07:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0004_openinghours'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='openinghours',
            options={'ordering': ['date'], 'verbose_name_plural': 'Opening hours'},
        ),
        migrations.AddField(
            model_name='openinghours',
            name='open',
            field=models.CharField(choices=[('open', 'open'), ('half', 'half day'), ('closed', 'closed')], default='open', max_length=64),
            preserve_default=False,
        ),
    ]