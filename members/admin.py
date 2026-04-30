from django.contrib import admin
from .models import (
    IndependentMember, MemberProgram, MemberProgramDay, MemberExercise,
    CoachConversation, CoachMessage, NutritionLog, PostureAnalysis,
)


@admin.register(IndependentMember)
class IndependentMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'activity_level', 'onboarding_complete', 'created_at')
    list_filter = ('activity_level', 'onboarding_complete', 'gender')
    search_fields = ('name', 'email')
    readonly_fields = ('created_at',)


class MemberExerciseInline(admin.TabularInline):
    model = MemberExercise
    extra = 0
    fields = ('exercise', 'sets', 'reps', 'notes', 'completed', 'order')


class MemberProgramDayInline(admin.TabularInline):
    model = MemberProgramDay
    extra = 0


@admin.register(MemberProgram)
class MemberProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'member', 'is_active', 'created_at')
    list_filter = ('is_active',)
    inlines = [MemberProgramDayInline]


@admin.register(NutritionLog)
class NutritionLogAdmin(admin.ModelAdmin):
    list_display = ('member', 'logged_date', 'total_calories', 'total_protein_g', 'created_at')
    list_filter = ('logged_date',)


@admin.register(PostureAnalysis)
class PostureAnalysisAdmin(admin.ModelAdmin):
    list_display = ('member', 'created_at')
    readonly_fields = ('ai_analysis',)


admin.site.register(CoachConversation)
admin.site.register(CoachMessage)
