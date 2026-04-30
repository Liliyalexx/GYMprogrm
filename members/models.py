from django.db import models
from django.contrib.auth.models import User


class IndependentMember(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('light', 'Light (1–2 days/week)'),
        ('moderate', 'Moderate (3–4 days/week)'),
        ('active', 'Active (5+ days/week)'),
        ('very_active', 'Very Active / Athlete'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member')
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    photo = models.ImageField(upload_to='member_photos/', null=True, blank=True)
    goals = models.TextField(blank=True)
    health_conditions = models.TextField(blank=True)
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, blank=True)
    doctor_prescription_file = models.FileField(upload_to='member_prescriptions/', null=True, blank=True)
    blood_test_file = models.FileField(upload_to='member_blood_tests/', null=True, blank=True)
    blood_analysis = models.JSONField(null=True, blank=True)
    photo_analysis = models.TextField(blank=True)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class MemberProgram(models.Model):
    member = models.ForeignKey(IndependentMember, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=200)
    ai_reasoning = models.TextField(blank=True)
    training_days_per_week = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.member.name}'


class MemberProgramDay(models.Model):
    program = models.ForeignKey(MemberProgram, on_delete=models.CASCADE, related_name='days')
    day_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f'Day {self.day_number}: {self.name}'


class MemberExercise(models.Model):
    day = models.ForeignKey(MemberProgramDay, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey('programs.ExerciseLibrary', on_delete=models.CASCADE)
    sets = models.CharField(max_length=50, blank=True)
    reps = models.CharField(max_length=50, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.exercise.name


class CoachConversation(models.Model):
    member = models.ForeignKey(IndependentMember, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.member.name} — {self.title or "New chat"}'


class CoachMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    conversation = models.ForeignKey(CoachConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class NutritionLog(models.Model):
    member = models.ForeignKey(IndependentMember, on_delete=models.CASCADE, related_name='nutrition_logs')
    logged_date = models.DateField()
    raw_input = models.TextField()
    items = models.JSONField(default=list)
    total_calories = models.FloatField(default=0)
    total_protein_g = models.FloatField(default=0)
    total_carbs_g = models.FloatField(default=0)
    total_fat_g = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_date', '-created_at']


class PostureAnalysis(models.Model):
    member = models.ForeignKey(IndependentMember, on_delete=models.CASCADE, related_name='posture_analyses')
    photo = models.ImageField(upload_to='member_posture/')
    ai_analysis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Posture — {self.member.name} — {self.created_at.date()}'


class ExerciseDemo(models.Model):
    """DALL-E generated demonstration images for an exercise."""
    exercise = models.OneToOneField(
        'programs.ExerciseLibrary', on_delete=models.CASCADE, related_name='demo'
    )
    image_start = models.ImageField(upload_to='exercise_demos/', null=True, blank=True)
    image_mid = models.ImageField(upload_to='exercise_demos/', null=True, blank=True)
    prompt_used = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Demo — {self.exercise.name}'
