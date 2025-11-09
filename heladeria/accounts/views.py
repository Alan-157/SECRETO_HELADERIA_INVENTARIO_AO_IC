# heladeria/accounts/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm, UserProfileEditForm# Importa el formulario que creaste
from django.contrib.auth import login # Opcional: si quieres loguear al usuario inmediatamente después del registro
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from .forms import PasswordResetRequestForm, PasswordResetVerifyForm
from .models import PasswordResetCode
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

# NOTA: La vista de login (LoginView) no está aquí, está en urls.py

def register_view(request):
    """
    Vista de función para el registro de nuevos usuarios.
    Maneja el envío del formulario (POST) y la visualización (GET).
    """
    if request.method == 'POST':
        # 1. Procesa la data del formulario
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, '¡Cuenta creada con éxito! Ahora espera activación por Administrador.')
            return redirect('accounts:login') 
        else:
            pass
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})

# Vistas para recuperación de contraseña


@require_http_methods(["GET","POST"])
def password_reset_request_view(request):
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.user
        PasswordResetCode.objects.filter(user=user, is_active=True).update(is_active=False)
        code = PasswordResetCode.generate_6_digits()
        PasswordResetCode.objects.create(user=user, code=code)

        current_site = get_current_site(request)
        ctx = {
            "site_name": current_site.name or "Sistema",
            "domain": current_site.domain or request.get_host(),
            "protocol": "https" if request.is_secure() else "http",
            "code": code,
            "minutes": 10,
        }

        subject = render_to_string("accounts/password/password_reset_subject.txt", ctx).strip()
        text_body = render_to_string("accounts/password/password_reset_email.txt", ctx)
        html_body = render_to_string("accounts/password/password_reset_email.html", ctx)

        msg = EmailMultiAlternatives(subject, text_body, to=[user.email])
        msg.attach_alternative(html_body, "text/html")
        msg.send()

        return redirect("accounts:password_reset_done")

    return render(request, "accounts/password/password_reset_form.html", {"form": form})


@require_http_methods(["GET","POST"])
def password_reset_verify_view(request):
    form = PasswordResetVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.user
        prc = form.prc
        user.set_password(form.cleaned_data["new_password"])
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["password", "failed_login_attempts", "locked_until"])
        prc.consume()
        return redirect("accounts:password_reset_complete")

    return render(request, "accounts/password/password_reset_confirm.html", {"form": form})

@login_required # Solo usuarios autenticados pueden acceder
def profile_edit(request):
    """
    Permite al usuario autenticado editar sus propios datos de perfil.
    """
    # Usamos la instancia del usuario autenticado
    user = request.user
    
    if request.method == 'POST':
        # Nota: si el formulario maneja ImageField (avatar), se debe pasar request.FILES
        form = UserProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            # Mensaje de éxito
            messages.success(request, '✅ Tu perfil ha sido actualizado correctamente.')
            return redirect('accounts:profile_edit') # Redirigir a la misma vista o al dashboard
        else:
            messages.error(request, '⚠️ Por favor, revisa los errores en el formulario.')
    else:
        # Petición GET: muestra el formulario con los datos actuales
        form = UserProfileEditForm(instance=user)

    context = {
        "form": form,
        "titulo": "Editar mi Perfil",
    }
    # La plantilla se creará en el siguiente paso
    return render(request, "accounts/profile_edit_form.html", context)