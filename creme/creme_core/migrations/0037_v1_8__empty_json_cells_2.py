# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-04 14:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0036_v1_8__empty_json_cells_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customblockconfigitem',
            name='json_cells',
            field=models.TextField(default=b'[]', editable=False),
        ),
        migrations.AlterField(
            model_name='relationblockitem',
            name='json_cells_map',
            field=models.TextField(default=b'{}', editable=False),
        ),
    ]
