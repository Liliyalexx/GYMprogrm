from django.contrib import admin
from .models import BodyMeasurement


@admin.register(BodyMeasurement)
class BodyMeasurementAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'weight_kg', 'body_fat_pct']
    list_filter = ['date']
