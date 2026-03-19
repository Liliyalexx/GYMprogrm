from django.urls import path
from . import views

app_name = 'programs'

urlpatterns = [
    path('student/<int:student_pk>/', views.program_list, name='list'),
    path('<int:pk>/', views.program_detail, name='detail'),
    path('student/<int:student_pk>/generate/', views.program_generate, name='generate'),
    path('<int:pk>/regenerate-nutrition/', views.regenerate_nutrition, name='regenerate_nutrition'),
    path('<int:pk>/backfill-english/', views.backfill_program_english, name='backfill_english'),
    path('<int:pk>/toggle-share/', views.toggle_share_section, name='toggle_share_section'),
    path('<int:pk>/retranslate/', views.retranslate_section, name='retranslate_section'),
    path('confirm-exercise/', views.confirm_exercise, name='confirm_exercise'),
    path('skip-exercise/', views.skip_exercise, name='skip_exercise'),
    path('exercises/', views.exercise_library, name='exercise_library'),
    path('exercises/create/', views.create_exercise, name='create_exercise'),
    path('exercises/add-to-program/', views.add_exercise_to_program, name='add_exercise_to_program'),
    path('exercises/add-to-day/', views.add_exercise_to_day, name='add_exercise_to_day'),
    path('exercises/delete/', views.delete_program_exercise, name='delete_program_exercise'),
    path('exercises/update/', views.update_program_exercise, name='update_program_exercise'),
    path('ai-correct/', views.ai_correct_text, name='ai_correct_text'),
    path('exercises/update-photo/', views.update_exercise_photo, name='update_exercise_photo'),
    path('exercises/generate-illustration/', views.generate_illustration, name='generate_illustration'),
    path('exercises/missing-illustrations/', views.generate_missing_illustrations, name='missing_illustrations'),
    path('exercises/create-warmup-stretch/', views.create_all_warmup_stretch, name='create_warmup_stretch'),
    path('templates/', views.template_list, name='template_list'),
    path('<int:pk>/save-as-template/', views.save_as_template, name='save_as_template'),
    path('templates/<int:template_pk>/assign/', views.assign_template, name='assign_template'),
    path('templates/<int:template_pk>/delete/', views.delete_template, name='delete_template'),
]
