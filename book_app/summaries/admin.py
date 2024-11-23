from django.contrib import admin
from .models import Book, UserProfile, UserActivity ,Bookmark,BookProgress,Category

# Register your models here.
admin.site.register(Book)
admin.site.register(UserProfile)
admin.site.register(UserActivity)
admin.site.register(Bookmark)
admin.site.register(BookProgress)
admin.site.register(Category)