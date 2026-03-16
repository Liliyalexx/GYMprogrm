from django.contrib import admin
from .models import BodyMeasurement


@admin.register(BodyMeasurement)
class BodyMeasurementAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'weight_kg']
    list_filter = ['date']
