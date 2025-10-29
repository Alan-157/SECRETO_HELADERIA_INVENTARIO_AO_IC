from django.db import models
from django.utils import timezone
from django.db.models import Q
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
    is_staff  = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    active_asignacion = models.ForeignKey(
        "UserPerfilAsignacion",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="usuarios_vigentes"
    )

    objects = CustomUserManager()
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['name']

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
