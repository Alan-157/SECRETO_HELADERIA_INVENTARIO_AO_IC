from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.db.models import Q
import secrets
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
import os

def validate_file_size_2mb(value):
    """Valida que el archivo no exceda 2MB (2 * 1024 * 1024 bytes)."""
    limit = 2 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('El tamaño máximo para el archivo es 2MB.')

# 1) BaseModel
class BaseModel(models.Model):
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

# 2) Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('El campo Email debe ser establecido')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuario debe tener is_superuser=True.')
        return self.create_user(email, name, password, **extra_fields)

# 3) Perfil (único por nombre)
class UserPerfil(BaseModel):
    nombre = models.CharField(max_length=20, unique=True)  # ← unique!
    def __str__(self):
        return self.nombre

class UsuarioApp(AbstractBaseUser, PermissionsMixin):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email = models.EmailField(unique=True, max_length=30)
    name  = models.CharField(max_length=20, blank=False)
    # ATENCIÓN: Se elimina unique=True del teléfono, ya que es demasiado restrictivo.
    phone = models.CharField(
        max_length=15, # Ajuste a 15 por si se incluye código de país (+56)
        unique=False,  # No único
        blank=True, null=True, # No requerido a nivel DB
        validators=[RegexValidator(r'^\+?\d{8,12}$', message='El teléfono debe ser un número válido.')],
        help_text="Teléfono de contacto (ej: +56912345678)"
    )

    avatar = models.ImageField(
        upload_to="users/", # Carpeta más simple
        null=True, blank=True,
        # Se añaden ambos validadores: extensión y tamaño (requisito de la evaluación)
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg","jpeg","png","webp"]),
            validate_file_size_2mb
        ],
        help_text="Imagen JPG/PNG. Máx 2MB."
    )

    is_staff  = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    
    # 👇 Campos de seguridad adicionales
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    # 👆

    active_asignacion = models.ForeignKey(
        "UserPerfilAsignacion",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="usuarios_vigentes"
    )

    # 👇 Métodos de seguridad adicionales
    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until

    def lock_for_minutes(self, minutes=15):
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.failed_login_attempts = 0 # Resetear intentos al bloquear
        self.save(update_fields=["locked_until", "failed_login_attempts"])
    # 👆

    objects = CustomUserManager()
    USERNAME_FIELD  = 'email'
    # Se añade 'phone' a REQUIRED_FIELDS (solo para el createsuperuser)
    REQUIRED_FIELDS = ['name',] # Quitamos 'phone' de REQUIRED_FIELDS porque en la práctica es mejor manejar la obligatoriedad en el form de edición, y para que las migraciones sean más limpias. Lo dejaremos opcional en el modelo.

    def __str__(self):
        return self.email


class PasswordResetCode(models.Model):
    user = models.ForeignKey(UsuarioApp, on_delete=models.CASCADE, related_name="reset_codes")
    code = models.CharField(max_length=6)  # solo números, lo validamos al crear
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    def consume(self):
        """Marca el código como usado (no reutilizable)."""
        self.is_active = False
        self.used_at = timezone.now()
        self.save(update_fields=["is_active", "used_at"])

    @staticmethod
    def generate_6_digits():
        # 000000–999999 preservando ceros a la izquierda
        return f"{secrets.randbelow(1_000_000):06d}"
    
# 5) Asignación (histórico + vigente)
class UserPerfilAsignacion(BaseModel):

    user   = models.ForeignKey(UsuarioApp, on_delete=models.CASCADE, related_name="asignaciones")
    perfil = models.ForeignKey(UserPerfil, on_delete=models.CASCADE, related_name="asignaciones")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "ended_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(ended_at__isnull=True),   # ← FIX: doble underscore
                name="uniq_user_asignacion_vigente"
            )
        ]

    @property
    def vigente(self):
        return self.ended_at is None

    def finalizar(self, when=None):
        if self.ended_at is None:
            self.ended_at = when or timezone.now()
            self.save(update_fields=["ended_at"])

    def __str__(self):
        return f"{self.user.email} → {self.perfil.nombre}"
