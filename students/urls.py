from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # Trainer views
    path('', views.student_list, name='list'),
    path('<int:pk>/', views.student_detail, name='detail'),
    path('new/', views.student_create, name='create'),
    path('<int:pk>/edit/', views.student_edit, name='edit'),
    path('<int:pk>/delete/', views.student_delete, name='delete'),
    path('<int:pk>/accept/', views.accept_intake, name='accept_intake'),
    path('<int:pk>/analyze-blood/', views.analyze_blood, name='analyze_blood'),
    path('<int:pk>/check-blood-analysis/', views.check_blood_analysis, name='check_blood_analysis'),
    path('<int:pk>/analyze-photo/', views.analyze_photo, name='analyze_photo'),
    path('<int:pk>/check-photo-analysis/', views.check_photo_analysis, name='check_photo_analysis'),
    path('<int:pk>/suggest-exercises-from-photo/', views.suggest_exercises_from_photo, name='suggest_exercises_from_photo'),
    path('<int:pk>/billing/', views.student_billing, name='billing'),
    path('<int:pk>/send-invite/', views.send_invite, name='send_invite'),
    path('<int:pk>/recommendation/save/', views.save_trainer_recommendation, name='save_trainer_recommendation'),
    path('<int:pk>/recommendation/confirm/', views.confirm_trainer_recommendation, name='confirm_trainer_recommendation'),
    path('payment-settings/', views.trainer_payment_settings, name='trainer_payment_settings'),

    # Student portal
    path('portal/', views.portal_dashboard, name='portal_dashboard'),
    path('portal/billing/', views.portal_billing, name='portal_billing'),
    path('portal/intake/', views.portal_intake, name='portal_intake'),
    path('portal/program/', views.portal_program, name='portal_program'),
    path('portal/log/<int:program_day_id>/', views.portal_log_workout, name='portal_log_workout'),
    path('portal/history/', views.portal_history, name='portal_history'),

    # Portal AI recommendations
    path('portal/recommendations/', views.portal_recommendations, name='portal_recommendations'),
    path('portal/get-recommendations/', views.portal_get_recommendations, name='portal_get_recommendations'),
    path('portal/check-recommendations/', views.portal_check_recommendations, name='portal_check_recommendations'),
    path('portal/request-program/', views.portal_request_program, name='portal_request_program'),

    # Doctor profiles (trainer)
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/new/', views.doctor_create, name='doctor_create'),
    path('doctors/<int:pk>/edit/', views.doctor_edit, name='doctor_edit'),
    path('doctors/<int:pk>/delete/', views.doctor_delete, name='doctor_delete'),
]
