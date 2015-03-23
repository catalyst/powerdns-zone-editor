# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Zone',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('zone_name', models.CharField(max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('comment', models.CharField(max_length=255)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ZoneRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rr_name', models.CharField(max_length=255)),
                ('rr_type', models.CharField(max_length=50)),
                ('rr_ttl', models.IntegerField()),
                ('rr_content', models.CharField(max_length=255)),
                ('zone', models.ForeignKey(to='client.Zone')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
