from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models import Avg, UniqueConstraint
from django.db.models.signals import post_save, post_delete
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
import fitz  # PyMuPDF
from textblob import TextBlob
from celery import shared_task


# Utility Function
def calculate_sentiment(text):
    """Calculate sentiment polarity using TextBlob."""
    if not text:
        return 0  # Neutral sentiment for empty reviews
    return TextBlob(text).sentiment.polarity


# Core Models
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    file = models.FileField(
        upload_to='pdfs/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        null=True,
        blank=True
    )
    categories = models.ManyToManyField(Category, related_name='books')
    sentiment = models.FloatField(default=0.0)
    is_recommended = models.BooleanField(default=False)
    content = models.TextField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} by {self.author}"

    def save(self, *args, **kwargs):
        if self.file and not self.content:
            process_pdf_content.delay(self.id)
        super().save(*args, **kwargs)

    def summarize(self):
        """Generate a basic summary from the content."""
        return self.content[:100] + '...' if self.content and len(self.content) > 100 else self.content

    def update_sentiment_from_reviews(self):
        """Update the book's sentiment based on related reviews."""
        reviews = self.reviews.all()
        self.sentiment = reviews.aggregate(avg_sentiment=Avg('sentiment_score'))['avg_sentiment'] or 0
        self.is_recommended = self.sentiment > 0
        self.save(update_fields=['sentiment','is_recommended'])


@shared_task
def process_pdf_content(book_id):
    """Asynchronous task to extract PDF content."""
    try:
        book = Book.objects.get(id=book_id)
        content = ""
        page_count = 0
        with fitz.open(book.file.path) as doc:
            for page in doc:
                content += page.get_text("text")
                page_count += 1
        book.content = content[:10000]  # Limit content length
        book.page_count = page_count
        book.save(update_fields=['content', 'page_count'])
    except Exception as e:
        # Handle exceptions if necessary
        print(f"Error processing PDF for Book ID {book_id}: {e}")


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    review_text = models.TextField(blank=True, null=True)
    sentiment_score = models.FloatField(default=0.0)
    star_rating = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Map star ratings to sentiment scores if review text is absent
        if not self.review_text:
            sentiment_mapping = {1: -1.0, 2: -0.5, 3: 0.0, 4: 0.5, 5: 1.0}
            self.sentiment_score = sentiment_mapping.get(self.star_rating, 0.0)
        else:
            self.sentiment_score = calculate_sentiment(self.review_text)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'book'], name='unique_user_book_review')
        ]


@receiver(post_save, sender=Review)
def update_book_sentiment_on_save(sender, instance, **kwargs):
    """Update book sentiment when a review is saved."""
    if instance.book:
        instance.book.update_sentiment_from_reviews()


@receiver(post_delete, sender=Review)
def update_book_sentiment_on_delete(sender, instance, **kwargs):
    """Update book sentiment when a review is deleted."""
    if instance.book:
        instance.book.update_sentiment_from_reviews()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    preferred_categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """Ensure a user profile is created or updated whenever a User instance is saved."""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.userprofile.save()


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    location = models.CharField(max_length=100)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.book.title} @ {self.location}"


class BookProgress(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')

    def __str__(self):
        return f"{self.book.title} - {self.status}"


class UserActivity(models.Model):
    ACTIVITY_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View Book'),
        ('bookmark', 'Bookmark Book'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"
