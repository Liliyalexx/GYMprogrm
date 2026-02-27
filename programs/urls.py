from django.urls import path
from . import views

app_name = 'programs'

urlpatterns = [
    path('student/<int:student_pk>/', views.program_list, name='list'),
    path('<int:pk>/', views.program_detail, name='detail'),
    path('student/<int:student_pk>/generate/', views.program_generate, name='generate'),
    path('<int:pk>/regenerate-nutrition/', views.regenerate_nutrition, name='regenerate_nutrition'),
    path('confirm-exercise/', views.confirm_exercise, name='confirm_exercise'),
    path('skip-exercise/', views.skip_exercise, name='skip_exercise'),
    path('exercises/', views.exercise_library, name='exercise_library'),
    path('exercises/add-to-program/', views.add_exercise_to_program, name='add_exercise_to_program'),
    path('ai-correct/', views.ai_correct_text, name='ai_correct_text'),
    path('exercises/update-photo/', views.update_exercise_photo, name='update_exercise_photo'),
]
