from django.db import models
from django.contrib.auth.models import User
from datetime import date
import uuid


class Student(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    INTAKE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending review'),
    ]
    PAYMENT_PLAN_CHOICES = [
        ('monthly', 'Monthly (2 programs)'),
        ('3months', '3 Months (6 programs)'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('venmo', 'Venmo'),
        ('paypal', 'PayPal'),
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('other', 'Other'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Payment Pending'),
        ('overdue', 'Overdue'),
    ]

    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='student')
    invite_token = models.UUIDField(null=True, blank=True)
    payment_plan = models.CharField(max_length=20, choices=PAYMENT_PLAN_CHOICES, default='monthly')
    payment_start_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_handle = models.CharField(max_length=200, blank=True, help_text='Venmo @handle, PayPal email/link, etc.')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, blank=True)

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
    training_days_per_week = models.PositiveSmallIntegerField(null=True, blank=True, help_text='How many days per week the client can train')
    follow_nutrition = models.BooleanField(default=False, help_text='Client agrees to follow nutrition recommendations')
    notes = models.TextField(blank=True)
    blood_analysis = models.JSONField(null=True, blank=True, help_text='Cached AI blood test analysis')
    photo_analysis = models.TextField(blank=True, help_text='Cached AI photo analysis')
    intake_status = models.CharField(max_length=20, choices=INTAKE_STATUS_CHOICES, default='active')
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
