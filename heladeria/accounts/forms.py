# heladeria/accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import UsuarioApp # Importamos Rol para la lógica de registro
from django.contrib.auth import get_user_model
User = get_user_model()

# --- REGISTER FORM (Formulario de Registro) ---
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

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password"), cd.get("password2")
        email = cd.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            self.add_error('email', "Este correo ya está en uso.")
        if p1 and p2:
            if not (8 <= len(p1) <= 20):
                self.add_error('password', "La contraseña debe tener entre 8 y 20 caracteres.")
            if p1 != p2:
                self.add_error('password2', "Las contraseñas no coinciden.")
        return cd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  # Registro 1: queda pendiente de activación
        user.set_password(self.cleaned_data["password"])
        if commit: user.save()
        return user
    
# --- LOGIN FORM (Formulario de Inicio de Sesión - Sin Cambios) ---
class LoginForm(AuthenticationForm): 
    
    remember_me = forms.BooleanField(required=False, label='Recordarme')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].label = "Correo Electrónico"
        
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Correo Electrónico'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña'})
        
        if 'remember_me' in self.fields:
            self.fields['remember_me'].widget.attrs.update({'class': 'form-check-input'})

# --- Formulario de templates
class UsuarioCreateForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "name")

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_active = False  # Se activa en el Registro 2 o admin
        if commit:
            user.save()
        return user


class UsuarioUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "name", "is_active")