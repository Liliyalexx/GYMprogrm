from django import forms
from .models import Student, DoctorProfile


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'gender', 'email', 'phone', 'date_of_birth',
                  'photo', 'blood_test_file', 'height_cm', 'weight_kg',
                  'health_issues', 'goals', 'notes']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'health_issues': forms.Textarea(attrs={'rows': 4}),
            'goals': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ['name', 'specialty', 'bio', 'photo_url', 'booking_link', 'compensation_note', 'is_active']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'compensation_note': forms.Textarea(attrs={'rows': 3}),
        }
