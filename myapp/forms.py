from django import forms
from .models import Test, Question
from .models import TestSourceDocument

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['course', 'title', 'description', 'due_date']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'option1', 'option2', 'option3', 'option4', 'correct_option']

class TestSourceDocumentForm(forms.ModelForm):
    class Meta:
        model = TestSourceDocument
        fields = ['course', 'title', 'uploaded_file']
