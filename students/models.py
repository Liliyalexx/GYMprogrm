from django.db import models
from datetime import date


class Student(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='student_photos/', null=True, blank=True)
    blood_test_file = models.FileField(upload_to='blood_tests/', null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text='Height in cm')
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text='Weight in kg')
    health_issues = models.TextField(blank=True, help_text='Injuries, conditions, contraindications')
    goals = models.TextField(blank=True, help_text='Client wishes: bigger glutes, lose fat, etc.')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
