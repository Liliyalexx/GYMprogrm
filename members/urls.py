from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    # Auth
    path('register/', views.member_register, name='register'),
    path('onboarding/', views.onboarding, name='onboarding'),

    # Core
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),

    # Program
    path('program/', views.program_list, name='program_list'),
    path('program/<int:pk>/', views.program_detail, name='program_detail'),
    path('program/generate/', views.generate_program_view, name='generate_program'),
    path('program/exercise/<int:exercise_id>/complete/', views.complete_exercise, name='complete_exercise'),

    # AI Coach Chat
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/new/', views.chat_new, name='chat_new'),
    path('chat/<int:pk>/', views.chat_room, name='chat_room'),
    path('chat/<int:pk>/send/', views.chat_send, name='chat_send'),
    path('chat/<int:pk>/generate-program/', views.chat_generate_program, name='chat_generate_program'),
    path('chat/<int:pk>/delete-conv/', views.chat_delete_conv, name='chat_delete_conv'),
    path('chat/bulk-delete/', views.chat_bulk_delete, name='chat_bulk_delete'),
    path('chat/<int:pk>/edit/<int:msg_id>/', views.chat_edit, name='chat_edit'),
    path('chat/<int:pk>/delete/<int:msg_id>/', views.chat_delete_msg, name='chat_delete_msg'),

    # Posture
    path('posture/', views.posture_list, name='posture_list'),
    path('posture/upload/', views.posture_upload, name='posture_upload'),
    path('posture/<int:pk>/', views.posture_detail, name='posture_detail'),

    # Nutrition
    path('nutrition/', views.nutrition_log, name='nutrition_log'),
    path('nutrition/<int:log_id>/add-again/', views.nutrition_add_again, name='nutrition_add_again'),

    # Progress
    path('progress/', views.progress, name='progress'),

    # Billing — Member
    path('billing/', views.billing_page, name='billing'),
    path('billing/checkout/', views.create_checkout_session, name='billing_checkout'),
    path('billing/addon/', views.addon_checkout, name='billing_addon'),
    path('billing/cancel-sub/', views.cancel_subscription, name='billing_cancel_sub'),
    path('billing/success/', views.checkout_success, name='billing_success'),
    path('billing/cancel/', views.checkout_cancel, name='billing_cancel'),

    # Billing — Trainer
    path('billing/trainer/', views.trainer_billing_page, name='trainer_billing'),
    path('billing/trainer/checkout/', views.trainer_create_checkout, name='trainer_billing_checkout'),
    path('billing/trainer/success/', views.checkout_success, name='trainer_billing_success'),
]
