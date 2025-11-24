from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.db.models import Q
import secrets
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError

# ============================================================
# VALIDADORES
# ============================================================

def validate_file_size_2mb(value):
    limit = 2 * 1024 * 1024  # 2 MB
    if value.size > limit:
        raise ValidationError("El tamaño máximo permitido es 2MB.")

# ============================================================
# BASE MODEL + MANAGER (ELIMINACIÓN LÓGICA)
# ============================================================

class ActiveManager(models.Manager):
    """Manager que oculta registros inactivos."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class BaseModel(models.Model):
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = ActiveManager()       # Solo activos
    objects_all = models.Manager()  # Incluye ocultos

    class Meta:
        abstract = True

    # Eliminación lógica estándar
    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.save(update_fields=["is_active"])

    # Eliminación lógica con hijos (si el modelo posee related_name="detalles")
    def soft_delete_with_children(self):
        self.is_active = False
        self.save(update_fields=["is_active"])
        if hasattr(self, "detalles"):
            self.detalles.update(is_active=False)

    # Eliminación física real
    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


# ============================================================
# CUSTOM USER MANAGER
# ============================================================

class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("El campo Email es obligatorio.")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuario debe tener is_superuser=True.")

        return self.create_user(email, name, password, **extra_fields)


# ============================================================
# PERFILES DEL SISTEMA
# ============================================================

class UserPerfil(BaseModel):
    nombre = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.nombre


# ============================================================
# USUARIO APP (NO HEREDA BaseModel — CORRECTO)
# ============================================================

class UsuarioApp(AbstractBaseUser, PermissionsMixin):
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    email       = models.EmailField(unique=True, max_length=30)
    name        = models.CharField(max_length=20)

    phone = models.CharField(
        max_length=15,
        blank=True, null=True,
        validators=[RegexValidator(r"^\+?\d{8,12}$", "El teléfono debe ser válido.")],
        help_text="Ejemplo: +56912345678"
    )

    avatar = models.ImageField(
        upload_to="users/",
        null=True, blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_file_size_2mb,
        ],
        help_text="Máximo 2MB."
    )

    is_staff  = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    # Seguridad adicional
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    active_asignacion = models.ForeignKey(
        "UserPerfilAsignacion",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="usuarios_vigentes"
    )

    # Métodos de bloqueo
    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until

    def lock_for_minutes(self, minutes=15):
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.failed_login_attempts = 0
        self.save(update_fields=["locked_until", "failed_login_attempts"])

    # Configuración del modelo usuario
    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email


# ============================================================
# CÓDIGOS DE RECUPERACIÓN
# ============================================================

class PasswordResetCode(models.Model):
    user = models.ForeignKey(UsuarioApp, on_delete=models.CASCADE, related_name="reset_codes")
    code = models.CharField(max_length=6)
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
        self.is_active = False
        self.used_at = timezone.now()
        self.save(update_fields=["is_active", "used_at"])

    @staticmethod
    def generate_6_digits():
        return f"{secrets.randbelow(1_000_000):06d}"


# ============================================================
# ASIGNACIÓN DE PERFILES
# ============================================================

class UserPerfilAsignacion(BaseModel):
    user   = models.ForeignKey(UsuarioApp, on_delete=models.CASCADE, related_name="asignaciones")
    perfil = models.ForeignKey(UserPerfil, on_delete=models.CASCADE, related_name="asignaciones")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "ended_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(ended_at__isnull=True),
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

