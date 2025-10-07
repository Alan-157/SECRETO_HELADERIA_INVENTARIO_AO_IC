# heladeria/accounts/forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import UsuarioApp, Rol # Importamos Rol para la lógica de registro


# --- REGISTER FORM (Formulario de Registro) ---
class RegisterForm(forms.ModelForm):
    password2 = forms.CharField(label='Confirmar Contraseña', widget=forms.PasswordInput()) 

    class Meta:
        model = UsuarioApp
        # AÑADIMOS EL CAMPO 'rol' PARA QUE APAREZCA EN EL HTML
        fields = ["name", "email", "rol", "password"] 
        # Aplicando estilos Bootstrap
        widgets = {
            "password": forms.PasswordInput(attrs={'class': 'form-control'}),
            "name": forms.TextInput(attrs={'class': 'form-control'}),
            "email": forms.EmailInput(attrs={'class': 'form-control'}),
            "rol": forms.Select(attrs={'class': 'form-select'}), # Estilo para el dropdown de roles
        }

    # Método clean() para manejar todas las validaciones
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")
        email = cleaned_data.get("email")

        # 1. Validar email (unicidad)
        if email and UsuarioApp.objects.filter(email=email).exists():
            self.add_error('email', "Este correo ya está en uso.")
        
        # 2. Validar reglas de contraseña y coincidencia
        if password and password2:
            if len(password) < 8 or len(password) > 20:
                self.add_error('password', "La contraseña debe tener entre 8 y 20 caracteres.")
            
            if password != password2:
                self.add_error('password2', "Las contraseñas no coinciden.") 
                
        return cleaned_data
    
    # Método save() para hashear la contraseña
    def save(self, commit=True):
        # El ModelForm AHORA guardará el rol seleccionado por el usuario.
        user = super().save(commit=False) 
        user.set_password(self.cleaned_data["password"]) # Hashear contraseña
        
        # *** SE ELIMINA LA LÓGICA DE ASIGNACIÓN AUTOMÁTICA DE ROL AQUÍ ***
        # El campo user.rol ya está seteado con el valor del formulario.
        
        if commit:
            user.save()
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