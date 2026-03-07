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
    path('<int:pk>/send-invite/', views.send_invite, name='send_invite'),

    # Student portal
    path('portal/', views.portal_dashboard, name='portal_dashboard'),
    path('portal/program/', views.portal_program, name='portal_program'),
    path('portal/log/<int:program_day_id>/', views.portal_log_workout, name='portal_log_workout'),
    path('portal/measurements/', views.portal_measurements, name='portal_measurements'),
    path('portal/history/', views.portal_history, name='portal_history'),
]
