from django.urls import path
from django.contrib.auth import views as auth_views
from .views import register_view # <-- ¡FALTABA ESTA IMPORTACIÓN!
from .forms import LoginForm 

app_name = "accounts"
urlpatterns = [
    # 0. Registro de Usuario (FALTABA ESTA RUTA)
    path('register/', register_view, name='register'), 

    # 1. Login y Logout (Vistas basadas en clases)
    path('login/', auth_views.LoginView.as_view(
        # Usamos la ruta simplificada para templates, si has movido los archivos:
        template_name='accounts/login.html', 
        authentication_form=LoginForm, 
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(), name='logout'), 

    # 2. Cambio de Contraseña (Protegido - requiere login)
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change_form.html',
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html',
    ), name='password_change_done'),

    # 3. Restablecimiento de Contraseña (No protegido)
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]