# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='source',
            field=models.CharField(default=b'file:///dev/null', max_length=200),
            preserve_default=True,
        ),
    ]