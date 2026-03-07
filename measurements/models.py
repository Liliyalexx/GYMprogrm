from django.db import models
from students.models import Student


class BodyMeasurement(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='measurements')
    date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    waist_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    hips_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    chest_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    arms_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    legs_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.student.name} — {self.date}'
