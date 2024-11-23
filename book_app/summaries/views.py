from django.shortcuts import render,redirect,get_object_or_404,resolve_url
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login,authenticate
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib.auth.views import LoginView
from transformers import T5Tokenizer, T5ForConditionalGeneration
from .models import (Book,Category,UserProfile,
                     BookProgress,Review,Bookmark,UserActivity)
import requests
import json
from .utils import *
from django.db.models import Q,Avg
import spacy
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from .serializers import BookSerializer,UserSerializer,UserProfileSerializer,UserActivitySerializer
from rest_framework import viewsets,status,generics
from django.http import JsonResponse,Http404,HttpResponse
import PyPDF2
from .forms import BookUploadForm
from django.views.decorators.csrf import csrf_protect,csrf_exempt,ensure_csrf_cookie
from django.contrib.auth.decorators import login_required, user_passes_test
import fitz
from .recommendation import get_recommendations
from textblob import TextBlob
from django.views.decorators.http import require_POST
import logging
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.db.models import Count
from django.views.generic import ListView
from django.core.files.storage import default_storage
from django.contrib import messages




logger = logging.getLogger(__name__)

tokenizer = T5Tokenizer.from_pretrained("t5-small")  # Options: t5-small, t5-base, t5-large
model = T5ForConditionalGeneration.from_pretrained("t5-small")

    
def recommended_books(request):
    recommended_books = []

    if request.user.is_authenticated:
        user_profile = request.user.userprofile
        preferred_categories = user_profile.preferred_categories.all()

        if preferred_categories.exists():
            recommended_books = Book.objects.filter(categories__in=preferred_categories).distinct()[:10]
        else:
            recommended_books = Book.objects.order_by('?')[:10]
    else:
        recommended_books = Book.objects.order_by('?')[:10]

    return render(request, 'recommendations.html', {'recommended_books': recommended_books})

def home(request): 
    # Fetch all categories
    categories = Category.objects.all()

    # Randomly select featured books
    featured_books = Book.objects.order_by('?')[:5]

    # Get popular books based on average star rating
    popular_books = Book.objects.annotate(
        avg_rating=Avg('reviews__star_rating')
    ).order_by('-avg_rating')[:5]

    recommendations = []
    recently_viewed = []
    profile = None

    # Check if the user is authenticated
    if request.user.is_authenticated:
        # Get user profile
        user_profile = get_object_or_404(UserProfile, user=request.user)

        # Get preferred categories if they exist
        preferred_categories = user_profile.preferred_categories.all()
        if preferred_categories.exists():
            # Get book recommendations based on preferred categories
            recommendations = Book.objects.filter(categories__in=preferred_categories).distinct()[:5]

        # Fallback to personalized recommendations using custom logic
        if not recommendations:
            recommended_ids = get_recommendations(request.user.id)
            recommendations = Book.objects.filter(id__in=recommended_ids)

        # Get recently viewed books using BookProgress
        recently_viewed_ids = list(
            BookProgress.objects.filter(user=request.user, status__in=['in_progress', 'completed'])
            .order_by('-id')
            .values_list('book__id', flat=True)[:5]
        )
        # Preserve order of recently viewed books
        recently_viewed = Book.objects.filter(id__in=recently_viewed_ids)
        recently_viewed = sorted(recently_viewed, key=lambda x: recently_viewed_ids.index(x.id))

        profile = user_profile
        recommended_books = Book.objects.filter(is_recommended=True)[:5]

    # Prepare context for rendering the template
    context = {
        'categories': categories,
        'featured_books': featured_books,
        'popular_books': popular_books,
        'recommended_books': recommended_books,
        'recently_viewed': recently_viewed,
        'profile': profile,
    }

    return render(request, 'home.html', context)



def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)  # Use Django's built-in user creation form
        if form.is_valid():
            user = form.save()  # Save the new user
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)  # Authenticate user
            login(request, user)  # Log the user in
            return redirect('dashboard')  # Redirect to the dashboard after successful registration
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form}) 

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Q

@login_required
def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')  # Redirect unauthenticated users to login

    # Get the profile of the currently logged-in user
    profile = get_object_or_404(UserProfile, user=request.user)

    # Gather recent activities
    recent_reviews = Review.objects.filter(user=request.user).order_by('-created_at')[:5]
    recent_bookmarks = Bookmark.objects.filter(user=request.user).order_by('-id')[:5]
    recent_progress = BookProgress.objects.filter(user=request.user).order_by('-id')[:5]

    # Annotate each activity with a type
    recent_reviews = [{"type": "review", "activity": review} for review in recent_reviews]
    recent_bookmarks = [{"type": "bookmark", "activity": bookmark} for bookmark in recent_bookmarks]
    recent_progress = [{"type": "progress", "activity": progress} for progress in recent_progress]

    # Combine activities and sort by timestamp/ID
    activities = sorted(
        recent_reviews + recent_bookmarks + recent_progress,
        key=lambda x: getattr(x["activity"], "created_at", getattr(x["activity"], "id", 0)),
        reverse=True
    )[:10]  # Limit to 10 most recent activities

    context = {
        'profile': profile,
        'activities': activities,
    }

    return render(request, 'dashboard.html', context)






def extract_text_from_pdf(pdf_path):
    """Extracts text from the given PDF file using PyMuPDF."""
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

def summarize_text(text, max_length=150, min_length=50):
    """Summarize text using T5."""
    input_text = f"summarize: {text}"
    inputs = tokenizer.encode(input_text, return_tensors="pt", truncation=True)

    summary_ids = model.generate(
        inputs,
        max_length=max_length,
        min_length=min_length,
        num_beams=4,  # Beam search for better summaries
        early_stopping=True
    )
    
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)


def summarize_large_text(text, max_chunk_size=1000, max_summary_length=150, min_summary_length=50):
    """Splits large text into chunks and summarizes each chunk separately."""
    text_chunks = [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]
    summaries = []

    for i, chunk in enumerate(text_chunks):
        try:
            summary = summarize_text(chunk, max_summary_length, min_summary_length)
            summaries.append(summary)
        except Exception as e:
            print(f"Error summarizing chunk {i}: {str(e)}")
            summaries.append("Error summarizing this section.")

    # Combine all chunk summaries into one summary text
    combined_summary = " ".join(summaries)
    return combined_summary

def summarize_book(request, book_id):
    if request.method == 'POST':
        try:
            book = Book.objects.get(id=book_id)
            if not book.summary:
                # Generate summary and save it
                book.summary = generate_summary(book.file.path)
                book.save()
                messages.success(request, "Summary generated successfully!")
            else:
                messages.info(request, "Summary already exists for this book.")
        except Book.DoesNotExist:
            messages.error(request, "Book not found.")
    return redirect('book_detail', book_id=book_id)
    

class BookRecommendationView(ListView):
    model = Book
    template_name = 'recommendations.html'
    context_object_name = 'recommendations'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            # Fetch the user's preferred categories
            user_profile = self.request.user.userprofile
            preferred_categories = user_profile.preferred_categories.all()

            if preferred_categories.exists():
                # Recommend books based on preferred categories
                context['recommendations'] = Book.objects.filter(
                    categories__in=preferred_categories
                ).distinct()[:10]
            else:
                # No preferences? Provide random books
                context['recommendations'] = Book.objects.order_by('?')[:10]
        else:
            # Random recommendations for guests
            context['recommendations'] = Book.objects.order_by('?')[:10]

        return context


@login_required
def progress_tracker(request):
    books = BookProgress.objects.filter(user=request.user)
    return render(request, 'progress_tracker.html', {'books': books})

def search_books(request):
    query = request.GET.get('q')  # Get the search query from the URL parameters
    results = []

    if query:  # If there is a query
        results = Book.objects.filter(title__icontains=query)  # Adjust field based on your model

    context = {
        'query': query,
        'results': results,
    }

    return render(request, 'search_books.html', context)

@login_required
def get_book_summary(request, book_id):
    book = Book.objects.get(id=book_id)
    summary = book.summarize()  # Assuming the summarize method exists
    return JsonResponse({'summary': summary})
    
nlp = spacy.load('en_core_web_sm')

def analyze_sentiment(text):
    blob = TextBlob(text)
    sentiment_score = blob.sentiment.polarity
    return sentiment_score
        
@api_view(['POST'])
def sentiment_analysis_view(request, book_id):
    try:
        book = Book.objects.get(id=book_id)
        metadata = f"{book.title} {book.author} {book.file}"

        # Calculate sentiment polarity
        blob = TextBlob(metadata)
        sentiment_score = blob.sentiment.polarity

        # Update and save sentiment score in the book record
        book.sentiment = sentiment_score
        book.save()

        return JsonResponse({"message": "Sentiment analyzed and saved.", "sentiment": sentiment_score})
    except Book.DoesNotExist:
        return JsonResponse({"error": "Book not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_books(request):
    """Fetches all books from the database."""
    books = list(Book.objects.values('id', 'title'))
    return JsonResponse(books, safe=False)


def get_book_suggestions(request):
    query = request.GET.get('query', '')
    if not query:
        return JsonResponse([], safe=False)

    try:
        # Use Internet Archive's API for fetching suggestions
        response = requests.get(f'https://archive.org/advancedsearch.php?q={query}&output=json', timeout=10)
        response.raise_for_status()  # Raises an exception for non-200 status codes

        data = response.json()
        if "response" not in data or "docs" not in data["response"]:
            return JsonResponse({"error": "Invalid response format"}, status=500)

        # Extract suggestions from the response
        suggestions = [
            {"title": doc.get("title", "Unknown Title")}
            for doc in data["response"].get("docs", [])
        ]
        return JsonResponse(suggestions, safe=False)

    except requests.exceptions.RequestException as e:
        # Handle request-related errors
        return JsonResponse({"error": str(e)}, status=500)

    except ValueError:
        # Handle JSON decoding errors
        return JsonResponse({"error": "Failed to parse JSON response"}, status=500)
    

def fetch_book_content(download_link):
    try:
        response = requests.get(download_link, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    

def upload_book(request):
    if request.method == 'POST':
        form = BookUploadForm(request.POST,request.FILES)
        if form.is_valid():
            book = form.save()
            if book.file.name.endswith('.pdf'):
                with open(book.file.path,'rb') as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    text = ''
                    for page in reader.pages:
                        text += page.extract_text()
                book.description = text
                book.save()
            return redirect('book_list')
    else:
        form = BookUploadForm()
    return render(request,'upload_book.html', {'form': form})


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    reviews = book.reviews.all()
    average_rating = book.reviews.aggregate(avg_rating=Avg('star_rating'))['avg_rating'] or 0
    rating_range = range(1, 6)
    context = {
        'book': book,
        'rating_range': rating_range,
        'average_rating': average_rating,
    }
    return render(request, 'book_detail.html', context)

def book_list(request):
    books = Book.objects.values('id', 'title')  # Fetch only required fields
    return JsonResponse(list(books), safe=False)
    
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

def category_books(request, category_id):
    books = Book.objects.filter(categories__id=category_id)
    book_list = [{'id': book.id, 'title': book.title, 'author': book.author} for book in books]
    return render(request, 'category_books.html',{'book_list': book_list})


@login_required
def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'user_profile.html', {'user': user})

@csrf_exempt
def user_activities(request):
    activities = UserActivity.objects.all().order_by('-timestamp')[:10]  # Fetch recent 10 activities
    activities_data = [
        {
            'id': activity.id,
            'activity_type': activity.activity_type,
            'timestamp': activity.timestamp,
        }
        for activity in activities
    ]
    return JsonResponse(activities_data, safe=False)

def csrf_token_view(request):
    csrf_token = get_token(request)
    response = JsonResponse({"csrfToken": csrf_token})
    response["Access-Control-Allow-Credentials"] = "true"
    return response


@ensure_csrf_cookie
def serve_react_app(request):
    return render(request, 'index.html')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    if request.user.is_authenticated:
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({"error": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)


@csrf_exempt
@api_view(['POST'])
def register_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, email=email)
        return JsonResponse({'message': 'User created successfully', 'user': username}, status=status.HTTP_201_CREATED)
    
    return JsonResponse({'error': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"message": "CSRF token set"})


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class UserActivityViewSet(viewsets.ModelViewSet):
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer

class CustomLoginView(LoginView):
    def get_success_url(self):
        user_id = self.request.user.id
        return resolve_url('dashboard', user_id=user_id)
    
def view_pdf(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{book.title}.pdf"'
    with open(book.file.path, 'rb') as pdf:
        response.write(pdf.read())
    return response

def summarize_pdf_view(request):
    if request.method == 'POST' and request.FILES['pdf']:
        pdf_file = request.FILES['pdf']
        pdf_path = default_storage.save(pdf_file.name, pdf_file)

        # Extract and summarize
        text = extract_text_from_pdf(pdf_path)
        summary = summarize_text(text)

        # Render the summary to a template
        return render(request, 'summary.html', {'summary': summary})
    return render(request, 'upload.html')

def all_books_view(request):
    books = Book.objects.all()  # Retrieve all books from the database
    return render(request, 'all_books.html', {'books': books})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_book(request, book_id):
    """
    Allows authenticated users to rate a book and updates the sentiment score.
    """
    try:
        # Use request.data to access parsed data
        star_rating = int(request.data.get('star_rating', 0))  # Extract rating

        if 1 <= star_rating <= 5:  # Validate rating range
            # Fetch the book or return a 404 if it doesn't exist
            book = get_object_or_404(Book, id=book_id)

            # Check if the user already reviewed the book
            review, created = Review.objects.get_or_create(
                user=request.user,
                book=book,
                defaults={'star_rating': star_rating}
            )

            if not created:
                # Update the existing review's star rating
                review.star_rating = star_rating
                review.save()

            # Update the book's sentiment score from its reviews
            reviews = book.reviews.all()
            if reviews.exists():
                avg_rating = reviews.aggregate(Avg('star_rating'))['star_rating__avg']
                book.sentiment = avg_rating  # Update sentiment score based on average rating
                book.save()

            return JsonResponse({'message': 'Rating submitted successfully.'})
        else:
            return JsonResponse({'error': 'Invalid rating. Must be between 1 and 5.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
