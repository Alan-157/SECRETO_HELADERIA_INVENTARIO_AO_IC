from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views, views_crud  
from .forms import LoginForm
from .views import CustomLoginView

app_name = "accounts"

urlpatterns = [
    # 0. Registro de Usuario
    path("register/", views.register_view, name="register"),

    # 1. Login / Logout
    path("login/", CustomLoginView.as_view(
        template_name="accounts/login.html",
        authentication_form=LoginForm,
    ), name="login"),

    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # 2. Cambio de contraseña
    path("password_change/", auth_views.PasswordChangeView.as_view(
        template_name="password/password_change_form.html",
    ), name="password_change"),

    path("password_change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="password/password_change_done.html",
    ), name="password_change_done"),

    # 3. Recuperación de contraseña
    path("password_reset/", auth_views.PasswordResetView.as_view(
        template_name="password/password_reset_form.html",
        email_template_name="password/password_reset_email.html",
        success_url=reverse_lazy("accounts:password_reset_done"),
    ), name="password_reset"),

    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="password/password_reset_done.html",
    ), name="password_reset_done"),

    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="password/password_reset_confirm.html",
    ), name="password_reset_confirm"),

    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="password/password_reset_complete.html",
    ), name="password_reset_complete"),

    #editar perfil
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # 4. CRUD de Usuarios y Perfiles (fuera del admin)
    path("usuarios/", views_crud.usuarios_list, name="usuarios_list"),
    path("usuarios/nuevo/", views_crud.usuarios_create, name="usuarios_create"),
    path("usuarios/<int:pk>/editar/", views_crud.usuarios_update, name="usuarios_update"),
    path("usuarios/<int:pk>/eliminar/", views_crud.usuarios_delete, name="usuarios_delete"),

    path("perfiles/", views_crud.perfiles_list, name="perfiles_list"),
    path("perfiles/nuevo/", views_crud.perfiles_create, name="perfiles_create"),
    path("perfiles/<int:pk>/editar/", views_crud.perfiles_update, name="perfiles_update"),
    path("perfiles/<int:pk>/eliminar/", views_crud.perfiles_delete, name="perfiles_delete"),

    path("password-reset/", views.password_reset_request_view, name="password_reset"),
    path("password-reset/verify/", views.password_reset_verify_view, name="password_reset_confirm"),
    path("password-reset/complete/", lambda r: render(r,"accounts/password/password_reset_complete.html"), name="password_reset_complete"),
]
