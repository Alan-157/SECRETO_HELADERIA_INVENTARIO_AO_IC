# heladeria/accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify  # opcional, por si quieres normalizar name

User = get_user_model()

# ---------- Utilidades opcionales ----------
DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "tempmail.com",
    "guerrillamail.com", "yopmail.com"
}

def _email_normalized(email: str) -> str:
    # Normaliza email para comparación (lowercase)
    return (email or "").strip().lower()

# ---------- REGISTER FORM ----------
class RegisterForm(forms.ModelForm):
    password2 = forms.CharField(label='Confirmar Contraseña', widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ["name", "email", "password"]
        widgets = {
            "name": forms.TextInput(attrs={'class': 'form-control'}),
            "email": forms.EmailInput(attrs={'class': 'form-control'}),
            "password": forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    # Email único + bloqueo dominios desechables (opcional)
    def clean_email(self):
        email = _email_normalized(self.cleaned_data.get("email"))
        if not email:
            raise ValidationError("Debes ingresar un correo.")
        # Bloquear dominios desechables: opcional
        domain = email.split("@")[-1]
        if domain in DISPOSABLE_DOMAINS:
            raise ValidationError("Este dominio de correo no es permitido.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Este correo ya está en uso.")
        return email

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres.")
        return name

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password"), cd.get("password2")
        email = cd.get("email")
        name = cd.get("name")

        # 1) Contraseñas coinciden
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Las contraseñas no coinciden.")

        # 2) Largo mínimo/máximo simple (mantiene tu regla original)
        if p1 and not (8 <= len(p1) <= 20):
            self.add_error('password', "La contraseña debe tener entre 8 y 20 caracteres.")

        # 3) No permitir contraseña igual a email o nombre
        if p1 and email and p1.lower() == str(email).lower():
            self.add_error('password', "La contraseña no puede ser igual al correo.")
        if p1 and name and p1.lower() == str(name).lower():
            self.add_error('password', "La contraseña no puede ser igual al nombre.")

        # 4) Validadores oficiales de Django (complejidad, comunes, etc.)
        if p1 and not self.errors.get('password'):
            try:
                validate_password(p1, user=None)  # puedes pasar instancia user si la tuvieras
            except ValidationError as e:
                self.add_error('password', e)

        return cd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  # Registro 1: queda pendiente de activación
        # Normaliza email
        user.email = _email_normalized(self.cleaned_data["email"])
        # Encripta contraseña
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# ---------- LOGIN FORM (sin cambios funcionales) ----------
class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label='Recordarme')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Correo Electrónico"
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Correo Electrónico'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña'})
        if 'remember_me' in self.fields:
            self.fields['remember_me'].widget.attrs.update({'class': 'form-check-input'})


# ---------- Formularios para templates (admin/gestión) ----------
class UsuarioCreateForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "name")

    def clean_email(self):
        email = _email_normalized(self.cleaned_data.get("email"))
        if not email:
            raise ValidationError("Debes ingresar un correo.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Este correo ya está en uso.")
        domain = email.split("@")[-1]
        if domain in DISPOSABLE_DOMAINS:
            raise ValidationError("Este dominio de correo no es permitido.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        name = cleaned.get("name")
        email = cleaned.get("email")

        if p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")

        if p1 and not (8 <= len(p1) <= 20):
            self.add_error('password1', "La contraseña debe tener entre 8 y 20 caracteres.")

        if p1 and email and p1.lower() == str(email).lower():
            self.add_error('password1', "La contraseña no puede ser igual al correo.")
        if p1 and name and p1.lower() == str(name).lower():
            self.add_error('password1', "La contraseña no puede ser igual al nombre.")

        if p1 and not self.errors.get('password1'):
            try:
                validate_password(p1, user=None)
            except ValidationError as e:
                self.add_error('password1', e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = _email_normalized(self.cleaned_data["email"])
        user.set_password(self.cleaned_data["password1"])
        user.is_active = False  # Se activa en el Registro 2 o admin
        if commit:
            user.save()
        return user


class UsuarioUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "name", "is_active")

    def clean_email(self):
        email = _email_normalized(self.cleaned_data.get("email"))
        if not email:
            raise ValidationError("Debes ingresar un correo.")
        # Evita duplicados al editar: excluir el propio id
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Este correo ya está en uso.")
        domain = email.split("@")[-1]
        if domain in DISPOSABLE_DOMAINS:
            raise ValidationError("Este dominio de correo no es permitido.")
        return email
