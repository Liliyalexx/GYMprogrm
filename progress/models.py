from django.db import models
from students.models import Student
from programs.models import ProgramDay, ProgramExercise


class WorkoutLog(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='workout_logs')
    program_day = models.ForeignKey(ProgramDay, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.student.name} — {self.date}'


class ExerciseLog(models.Model):
    workout_log = models.ForeignKey(WorkoutLog, on_delete=models.CASCADE, related_name='exercise_logs')
    program_exercise = models.ForeignKey(ProgramExercise, on_delete=models.SET_NULL, null=True, blank=True)
    exercise_name = models.CharField(max_length=200)
    sets_done = models.PositiveSmallIntegerField(default=0)
    reps_done = models.CharField(max_length=50, blank=True, help_text='E.g. "10,10,8"')
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.exercise_name} — {self.workout_log}'
