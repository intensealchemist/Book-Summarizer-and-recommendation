# Generated by Django 5.1.2 on 2024-11-17 16:42

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('summaries', '0008_alter_book_cover_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='sentiment',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='favourite_books',
            field=models.ManyToManyField(blank=True, to='summaries.book'),
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='preferred_categories',
            field=models.ManyToManyField(blank=True, to='summaries.category'),
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('review_text', models.TextField()),
                ('sentiment_score', models.FloatField(default=0.0)),
                ('star_rating', models.PositiveSmallIntegerField(default=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='summaries.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
