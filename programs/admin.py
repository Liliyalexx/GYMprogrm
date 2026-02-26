from django.contrib import admin
from .models import ExerciseLibrary, WorkoutProgram, ProgramDay, ProgramExercise


@admin.register(ExerciseLibrary)
class ExerciseLibraryAdmin(admin.ModelAdmin):
    list_display = ['name', 'muscle_group', 'difficulty']
    list_filter = ['muscle_group', 'difficulty']
    search_fields = ['name']


class ProgramExerciseInline(admin.TabularInline):
    model = ProgramExercise
    extra = 0


class ProgramDayInline(admin.TabularInline):
    model = ProgramDay
    extra = 0


@admin.register(WorkoutProgram)
class WorkoutProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'student', 'is_active', 'created_at']
    inlines = [ProgramDayInline]


@admin.register(ProgramDay)
class ProgramDayAdmin(admin.ModelAdmin):
    list_display = ['name', 'program', 'day_number']
    inlines = [ProgramExerciseInline]
