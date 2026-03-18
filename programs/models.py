from django.db import models
from students.models import Student


class ExerciseLibrary(models.Model):
    MUSCLE_GROUP_CHOICES = [
        ('glutes', 'Glutes'),
        ('legs', 'Legs'),
        ('back', 'Back'),
        ('chest', 'Chest'),
        ('shoulders', 'Shoulders'),
        ('arms', 'Arms'),
        ('core', 'Core'),
        ('cardio', 'Cardio'),
        ('full_body', 'Full Body'),
    ]
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    name = models.CharField(max_length=200)
    photo_url = models.URLField(blank=True, max_length=2000)
    description = models.TextField(help_text='What to do and which muscles are worked')
    posture_tips = models.TextField(blank=True, help_text='AI-generated posture & technique tips')
    muscle_group = models.CharField(max_length=50, choices=MUSCLE_GROUP_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')

    class Meta:
        ordering = ['muscle_group', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_muscle_group_display()})'


class WorkoutProgram(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)
    name_ru = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    training_days = models.PositiveSmallIntegerField(default=3)
    nutrition_plan = models.JSONField(null=True, blank=True)
    nutrition_plan_en = models.JSONField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    duration_weeks = models.PositiveSmallIntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # Keys: 'goals', 'analysis', 'nutrition' — True means confirmed to share with student
    shared_sections = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.student.name}'


class ProgramDay(models.Model):
    program = models.ForeignKey(WorkoutProgram, on_delete=models.CASCADE, related_name='days')
    day_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200, help_text='E.g. "Day 1 — Glutes & Legs"')
    name_en = models.CharField(max_length=200, blank=True)
    name_ru = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f'{self.program.name} / {self.name}'


class ProgramExercise(models.Model):
    program_day = models.ForeignKey(ProgramDay, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(ExerciseLibrary, on_delete=models.PROTECT)
    sets = models.PositiveSmallIntegerField(default=3)
    reps = models.CharField(max_length=20, default='10', help_text='E.g. "10", "8-12", "30 sec"')
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    name_ru = models.CharField(max_length=200, blank=True)
    reason_ru = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    confirmed = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.exercise.name} — {self.program_day}'
