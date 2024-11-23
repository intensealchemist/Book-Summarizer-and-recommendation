# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Book
from .utils import extract_text_from_pdf, summarize_text

@receiver(post_save, sender=Book)
def generate_summary_for_new_pdf(sender, instance, created, **kwargs):
    if created and instance.file and not instance.summary:
        try:
            # Extract text and summarize
            text = extract_text_from_pdf(instance.file.path)
            summary = summarize_text(text)

            # Save the summary
            instance.summary = summary
            instance.save()
        except Exception as e:
            print(f"Failed to summarize {instance.title}: {e}")
