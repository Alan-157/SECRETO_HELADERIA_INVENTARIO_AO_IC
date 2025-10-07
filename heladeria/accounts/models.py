from django.db import models
# Importamos las clases base requeridas por Django para un modelo de usuario custom
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# --- 1. BASE MODEL (para campos de auditoría) ---
# Esta es la clase que deben heredar Categoria, Insumo, etc.
class BaseModel(models.Model):
    # <-- ¡AÑADIR ESTE CAMPO DE VUELTA!
    is_active = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

# --- 2. CUSTOM USER MANAGER (Manejador de creación de usuarios) ---
class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('El campo Email debe ser establecido')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        # set_password hashea la contraseña, crucial para seguridad
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        # Campos por defecto para superusuario
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuario debe tener is_superuser=True.')
            
        return self.create_user(email, name, password, **extra_fields)

# --- 3. MODELOS DE ROL Y PERFIL ---
class Rol(BaseModel): # <-- Ahora Rol hereda is_active
    nombre = models.CharField(max_length=50)

class UserPerfil(BaseModel): 
    nombre = models.CharField(max_length=100)
    def __str__(self): return self.nombre


# --- 4. USUARIOAPP (El AUTH_USER_MODEL) ---
class UsuarioApp(AbstractBaseUser, PermissionsMixin):
    """Modelo de Usuario Personalizado que usa email como identificador."""
    
    # Auditoría (copiados de BaseModel)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Campos de identificación
    email = models.EmailField(verbose_name='email address', unique=True)
    name = models.CharField(max_length=100, blank=False)
    
    # Campos de PermissionsMixin / Status (Manejo de permisos y Admin)
    is_staff = models.BooleanField(default=False) # Permite acceso a /admin/
    is_active = models.BooleanField(default=True) # Permite iniciar sesión

    # Campos FK de tu ERD
    user_perfil = models.ForeignKey(
        UserPerfil, on_delete=models.PROTECT, related_name="usuarios", null=True, blank=True
    )
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="usuarios", null=True, blank=True)

    # Requerimientos del sistema de autenticación de Django (Respuesta al AttributeError)
    objects = CustomUserManager() # Asigna el manager custom
    USERNAME_FIELD = 'email'     # Usa email como campo de inicio de sesión
    REQUIRED_FIELDS = ['name']   # Campos requeridos por createsuperuser

    def __str__(self):
        return self.email

    # Métodos requeridos por CustomUser
    def get_full_name(self): return self.name
    def get_short_name(self): return self.name


# --- 5. ASIGNACIÓN (Relación N:M) ---
class UserPerfilAsignacion(BaseModel): 
    user = models.ForeignKey(UsuarioApp, on_delete=models.CASCADE, related_name="asignaciones")
    perfil = models.ForeignKey(UserPerfil, on_delete=models.CASCADE, related_name="asignaciones")
    activo = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta: # No heredamos de BaseModel.Meta para evitar conflicto con BaseModel anterior
        unique_together = ("user", "perfil")
    def __str__(self): return f"{self.user.email} → {self.perfil.nombre}"