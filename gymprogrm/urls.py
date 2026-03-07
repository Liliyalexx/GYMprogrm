from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from students import views as student_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('auth/redirect/', student_views.auth_redirect, name='auth_redirect'),
    path('intake/', student_views.client_intake, name='intake'),
    path('intake/success/', student_views.intake_success, name='intake_success'),
    path('invite/<uuid:token>/', student_views.invite_register, name='invite_register'),
    path('students/', include('students.urls', namespace='students')),
    path('programs/', include('programs.urls', namespace='programs')),
    path('', lambda request: redirect('students:list'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
