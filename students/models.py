from django.db import models
from datetime import date


class Student(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='student_photos/', null=True, blank=True)
    blood_test_file = models.FileField(upload_to='blood_tests/', null=True, blank=True)
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
