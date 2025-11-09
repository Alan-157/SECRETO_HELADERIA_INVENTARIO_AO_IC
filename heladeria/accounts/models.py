from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.db.models import Q
import secrets
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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
    nombre = models.CharField(max_length=100, unique=True)  # ← unique!
    def __str__(self):
        return self.nombre

# 4) Usuario
class UsuarioApp(AbstractBaseUser, PermissionsMixin):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email = models.EmailField(unique=True, max_length=191)
    name  = models.CharField(max_length=100, blank=False)
    phone = models.CharField(
        max_length=9,
        unique=True,
        validators=[RegexValidator(r'^\d{9}$', message='Debe tener exactamente 9 dígitos.')],
        help_text="Teléfono celular de 9 dígitos (ej: 912345678)"
    )

    avatar = models.ImageField(
        upload_to="media/users/",
        null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg","jpeg","png"])],
        help_text="Imagen JPG/PNG. Máx 2MB."
    )

    is_staff  = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    active_asignacion = models.ForeignKey(
        "UserPerfilAsignacion",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="usuarios_vigentes"
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until

    def lock_for_minutes(self, minutes=15):
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=["locked_until"])

    objects = CustomUserManager()
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['name','phone']

    def __str__(self):
        return self.email
    def get_full_name(self):  
        return self.name
    def get_short_name(self): 
        return self.name

    # ← alias de compatibilidad para mantener "role" en vistas/templates/seeds
    @property
    def role(self):
        asg = getattr(self, "active_asignacion", None)
        return getattr(getattr(asg, "perfil", None), "nombre", None)


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
