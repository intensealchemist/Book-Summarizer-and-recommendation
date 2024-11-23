from django import forms 
from .models import Book

class BookUploadForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'file', 'categories']
        widgets = {
            'categories': forms.CheckboxSelectMultiple(),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file', False)
        if file:
            if not file.name.endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed.")
        return file
