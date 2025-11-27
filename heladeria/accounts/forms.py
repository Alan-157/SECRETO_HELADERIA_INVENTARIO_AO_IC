# heladeria/accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import PasswordResetCode
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify  # opcional, por si quieres normalizar name

User = get_user_model()

# ---------- Utilidades opcionales ----------
DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "tempmail.com",
    "guerrillamail.com", "yopmail.com"
}

MAX_AVATAR_MB = 2

def _validate_avatar(file):
    if not file:
        return
    # Tamaño
    if file.size > MAX_AVATAR_MB * 1024 * 1024:
        raise ValidationError(f"La imagen no puede superar {MAX_AVATAR_MB}MB.")
    # Mimetype simple
    ctype = (getattr(file, "content_type", "") or "").lower()
    if not (ctype.startswith("image/jpeg") or ctype.startswith("image/png") or ctype.startswith("image/webp")):
        raise ValidationError("Solo se permiten imágenes JPG o PNG.")

def _email_normalized(email: str) -> str:
    # Normaliza email para comparación (lowercase)
    return (email or "").strip().lower()


# ---------- PASSWORD RESET FORMS ----------
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        email = (self.cleaned_data["email"] or "").strip().lower()
        try:
            self.user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # no reveles que no existe: mensaje genérico
            raise ValidationError("Si el correo es válido, recibirás un código de verificación.")
        if self.user.is_locked():
            raise ValidationError("La cuenta está temporalmente bloqueada.")
        return email
    
class PasswordResetVerifyForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(min_length=6, max_length=6)
    new_password = forms.CharField(widget=forms.PasswordInput)
    new_password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cd = super().clean()
        email = (cd.get("email") or "").strip().lower()
        code  = cd.get("code") or ""
        if not email or not code:
            return cd
        try:
            self.user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ValidationError("Código inválido o expirado.")

        qs = PasswordResetCode.objects.filter(user=self.user, code=code, is_active=True)
        prc = qs.order_by("-created_at").first()
        if not prc or prc.is_expired():
            raise ValidationError("Código inválido o expirado.")

        p1, p2 = cd.get("new_password"), cd.get("new_password2")
        if p1 != p2:
            self.add_error("new_password2", "Las contraseñas no coinciden.")

        self.prc = prc
        return cd    
# ---------- REGISTER FORM ----------
class RegisterForm(forms.ModelForm):
    password2 = forms.CharField(label='Confirmar Contraseña', widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ["name", "email", "phone", "avatar", "password"]
        widgets = {
            "name": forms.TextInput(attrs={'class': 'form-control'}),
            "email": forms.EmailInput(attrs={'class': 'form-control'}),
            "phone": forms.TextInput(attrs={'class': 'form-control'}),
            "avatar": forms.ClearableFileInput(attrs={'class': 'form-control'}),
            "password": forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    # Email único + bloqueo dominios desechables (opcional)
    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone.isdigit() or len(phone) != 9:
            raise ValidationError("El teléfono debe tener exactamente 9 dígitos.")
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("Este teléfono ya está registrado.")
        return phone
    
    def clean_avatar(self):
        file = self.cleaned_data.get("avatar")
        _validate_avatar(file)
        return file
    
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
    def confirm_login_allowed(self, user):
        if hasattr(user, "is_locked") and user.is_locked():
            raise ValidationError(
                "Tu cuenta está temporalmente bloqueada por intentos fallidos. Intenta más tarde.",
                code="locked",
            )
        if not user.is_active:
            raise ValidationError("Tu cuenta no está activa.", code="inactive")

# ---------- Formularios para templates (admin/gestión) ----------
class UsuarioCreateForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "name","phone", "avatar")

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone.isdigit() or len(phone) != 9:
            raise ValidationError("El teléfono debe tener exactamente 9 dígitos.")
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("Este teléfono ya está registrado.")
        return phone

    def clean_avatar(self):
        file = self.cleaned_data.get("avatar")
        _validate_avatar(file)
        return file

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
        fields = ("email", "name","phone", "avatar", "is_active")

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone.isdigit() or len(phone) != 9:
            raise ValidationError("El teléfono debe tener exactamente 9 dígitos.")
        qs = User.objects.filter(phone=phone)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Este teléfono ya está registrado.")
        return phone

    def clean_avatar(self):
        file = self.cleaned_data.get("avatar")
        _validate_avatar(file)
        return file
    
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


class UserProfileEditForm(forms.ModelForm):
    """
    Formulario para que el usuario edite sus propios datos (nombre, correo, teléfono, avatar).
    """
    class Meta:
        model = User
        fields = ("name", "email", "phone", "avatar")
        widgets = {
            "name": forms.TextInput(attrs={'class': 'form-control'}),
            "email": forms.EmailInput(attrs={'class': 'form-control'}),
            "phone": forms.TextInput(attrs={'class': 'form-control'}),
            # Importante: Asegurar que el campo de archivo tenga la clase form-control
            "avatar": forms.FileInput(attrs={'class': 'form-control'}), 
        }
        labels = {
            "name": "Nombre completo",
            "email": "Correo Electrónico",
            "phone": "Teléfono",
            "avatar": "Imagen de Perfil (Avatar)",
        }

    def clean_email(self):
        """Valida unicidad del email, excluyendo al usuario actual."""
        email = _email_normalized(self.cleaned_data.get("email"))
        if not email:
            raise ValidationError("Debes ingresar un correo.")
        
        # Excluir el propio id de la búsqueda de duplicados
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise ValidationError("Este correo ya está en uso.")

        domain = email.split("@")[-1]
        if domain in DISPOSABLE_DOMAINS:
            raise ValidationError("Este dominio de correo no es permitido.")
            
        return email
    
