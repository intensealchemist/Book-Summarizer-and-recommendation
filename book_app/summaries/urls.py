# book_app/urls.py (or summaries/urls.py, depending on your app's name)
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Web views (Frontend)
    path('', views.home, name='home'),  # Home page
    path('category/<int:category_id>/', views.category_books, name='category_books'),  # View books by category
    path('search/', views.search_books, name='search_books'),  # Search for books
    path('book/<int:book_id>/summary/', views.get_book_summary, name='get_book_summary'),  # Book summary view
    path('books/', views.all_books_view, name='all_books'),  # Page to display all books
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),  # Book detail page
    path('register/', views.register, name='register'),  # User registration
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),  # User login
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),  # User logout
    path('dashboard/', views.dashboard_view, name='dashboard'),  # User dashboard
    # path('profile/<str:username>/', views.user_profile, name='user_profile'),  # User profile page
    path('upload/', views.upload_book, name='upload_book'),  # Book upload page
    path('recommendations/', views.BookRecommendationView.as_view(), name='recommendations'),  # Book recommendations
    path('progress/', views.progress_tracker, name='progress_tracker'),  # Progress tracking
    path('book/<int:book_id>/pdf/', views.view_pdf, name='view_pdf'),  # PDF view for a book
    path('summarize/', views.summarize_pdf_view, name='summarize_pdf'),  # PDF summarization view
    path('profile/', views.user_profile, name='user_profile'),
    path('rate-book/<int:book_id>/', views.rate_book, name='rate_book'),
    path('recommended/',views.recommended_books, name='recommended_books'),

    # API views

    path('api/books/', views.book_list, name='api_book_list'),  # API for list of books
    path('api/books/<int:book_id>/', views.book_detail, name='api_book_detail'),  # API for a single book's detail
    path('books/<int:book_id>/summarize/', views.summarize_book, name='summarize_book'),  # Summarize a specific book
    path('api/profile/<str:username>/', views.user_profile, name='user_profile'),
    path('api/useractivities/', views.user_activities, name='api_user_activities'),  # API for user activities
]