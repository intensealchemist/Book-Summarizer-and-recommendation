# Generated by Django 5.1.2 on 2024-11-03 09:50

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('summaries', '0004_userinteraction_review_userinteraction_sentiment_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bookprogress',
            name='author',
        ),
        migrations.RemoveField(
            model_name='bookprogress',
            name='title',
        ),
        migrations.AddField(
            model_name='bookprogress',
            name='book',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='summaries.book'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='preferred_categories',
            field=models.ManyToManyField(blank=True, to='summaries.category'),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]