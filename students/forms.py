from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'gender', 'email', 'phone', 'date_of_birth',
                  'photo', 'blood_test_file', 'height_cm', 'weight_kg',
                  'health_issues', 'goals', 'notes',
                  'payment_plan', 'payment_start_date',
                  'payment_method', 'payment_handle', 'payment_status']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'payment_start_date': forms.DateInput(attrs={'type': 'date'}),
            'health_issues': forms.Textarea(attrs={'rows': 4}),
            'goals': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
