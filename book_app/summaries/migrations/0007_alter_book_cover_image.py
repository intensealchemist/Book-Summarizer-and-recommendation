# Generated by Django 5.1.2 on 2024-11-14 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('summaries', '0006_book_cover_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='book',
            name='cover_image',
            field=models.ImageField(blank=True, null=True, upload_to='book_app/book_covers/'),
        ),
    ]