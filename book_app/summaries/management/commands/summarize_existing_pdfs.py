# yourapp/management/commands/summarize_existing_pdfs.py
from django.core.management.base import BaseCommand
from summaries.models import Book
from summaries.utils import extract_text_from_pdf, summarize_text

class Command(BaseCommand):
    help = 'Generates summaries for all existing PDFs without a summary.'

    def handle(self, *args, **kwargs):
        books = Book.objects.filter(summary__isnull=True)
        for book in books:
            try:
                # Extract text from PDF
                pdf_path = book.file.path
                text = extract_text_from_pdf(pdf_path)

                # Generate summary
                summary = summarize_text(text)

                # Save summary in database
                book.summary = summary
                book.save()

                self.stdout.write(self.style.SUCCESS(f'Summary created for: {book.title}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to summarize {book.title}: {e}'))
