from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from students import views as student_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html', email_template_name='registration/password_reset_email.txt', subject_template_name='registration/password_reset_subject.txt'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    # Google OAuth
    path('accounts/', include('allauth.urls')),
    path('auth/redirect/', student_views.auth_redirect, name='auth_redirect'),
    path('auth/no-profile/', student_views.no_student_profile, name='no_student_profile'),
    path('intake/', student_views.client_intake, name='intake'),
    path('intake/success/', student_views.intake_success, name='intake_success'),
    path('invite/<uuid:token>/', student_views.invite_register, name='invite_register'),
    path('send-intake-email/', student_views.send_intake_email, name='send_intake_email'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('students/', include('students.urls', namespace='students')),
    path('programs/', include('programs.urls', namespace='programs')),
    path('', lambda request: redirect('students:list'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
