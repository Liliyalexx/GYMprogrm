from django.contrib import admin
from .models import WorkoutLog, ExerciseLog


class ExerciseLogInline(admin.TabularInline):
    model = ExerciseLog
    extra = 0


@admin.register(WorkoutLog)
class WorkoutLogAdmin(admin.ModelAdmin):
    list_display = ['student', 'program_day', 'date', 'completed']
    list_filter = ['completed', 'date']
    inlines = [ExerciseLogInline]


@admin.register(ExerciseLog)
class ExerciseLogAdmin(admin.ModelAdmin):
    list_display = ['exercise_name', 'workout_log', 'sets_done', 'weight_kg']
