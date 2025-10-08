from urllib import request
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from .models import Rol, UserPerfil, UsuarioApp, UserPerfilAsignacion 

# --- ACCIONES PERSONALIZADAS: Activar/Desactivar (Clase U2 C3) ---
def rol_name(user):
    try:
        return (user.rol.nombre or "").lower()
    except Exception:
        return ""
@admin.action(description="Activar perfiles seleccionados")
def activar_perfiles(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} perfil(es) activado(s).", messages.SUCCESS)

@admin.action(description="Desactivar perfiles seleccionados")
def desactivar_perfiles(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} perfil(es) desactivado(s).", messages.WARNING)

@admin.action(description="Activar usuarios seleccionados")
def activar_usuarios(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} usuario(s) activado(s).", messages.SUCCESS)

@admin.action(description="Desactivar usuarios seleccionados")
def desactivar_usuarios(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} usuario(s) desactivado(s).", messages.WARNING)


# --- INLINE & VALIDACIÓN (Para gestionar asignaciones desde el Perfil) ---
class AsignacionInlineFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Recolectar usuarios marcados como activos en este formset
        activos_users = []
        for form in self.forms:
            # forms vacíos o eliminados no se consideran
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            # Solo consideramos filas marcadas como activas
            if form.cleaned_data.get("activo"):
                user = form.cleaned_data.get("user")
                if user is None:
                    # Si activo=True pero sin usuario, es inválido
                    raise ValidationError("Debe seleccionar un usuario para activar la asignación.")
                activos_users.append(user)
        # Si hay duplicados en usuarios activos -> error
        if len(set(activos_users)) < len(activos_users):
            raise ValidationError("Cada usuario puede tener solo una asignación activa en este perfil.")


class UserPerfilAsignacionInline(admin.TabularInline):
    model = UserPerfilAsignacion
    formset = AsignacionInlineFormset
    extra = 0
    fields = ("user", "activo", "assigned_at")
    readonly_fields = ("assigned_at",)
    show_change_link = True
    verbose_name = "Asignación de usuario"
    verbose_name_plural = "Asignaciones de usuarios"

# --- REGISTROS DE ADMIN ---

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("nombre",)
    ordering = ("nombre",)

@admin.register(UserPerfil)
class UserPerfilAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("nombre",)
    ordering = ("nombre",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [UserPerfilAsignacionInline] # <-- Uso de Inline (Clase U2 C3)
    actions = [activar_perfiles, desactivar_perfiles]
    
    # Permisos de módulo (visibilidad en el menú lateral)
    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return False  # Solo superusuarios pueden ver el módulo
    
    # Filtrado por perfil del usuario logueado
    """Si el usuario no es superusuario, solo ve su propio perfil."""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        user_perfil = getattr(request.user, "user_perfil", None)
        return qs.filter(id=user_perfil.id) if user_perfil else qs.none()


@admin.register(UsuarioApp)
class UsuarioAppAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name", "rol", "user_perfil", "is_active", "updated_at")
    # Filtra por estado (is_active), perfil y rol
    list_filter = ("is_active", "user_perfil", "rol") 
    search_fields = ("email", "name", "user_perfil__nombre", "rol__nombre") # Búsqueda por FK
    ordering = ("email",)
    readonly_fields = ("created_at", "updated_at")
    actions = [activar_usuarios, desactivar_usuarios]

    # Permisos de módulo (visibilidad en el menú lateral)
    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        # Permitir si el rol del usuario es 'admin' o 'manager'
        user_rol = rol_name(request.user)
        if user_rol in ["admin", "manager"]:
            return True
        return False  # Otros roles no pueden ver el módulo
    
    # Permisos de acceso (ver, agregar, cambiar, eliminar)
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_add_permission(self, request):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    # Filtrado por perfil del usuario logueado
    """Si el usuario no es superusuario, solo ve su propio usuario."""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        user_perfil = getattr(request.user, 'user_perfil', None)
        return qs.filter(user_perfil=user_perfil) if user_perfil else qs.none()
    
    #   Restringir acciones sensibles si no es superusuario
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(UserPerfilAsignacion)
class UserPerfilAsignacionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "perfil", "activo", "assigned_at")
    list_filter = ("activo", "perfil")
    search_fields = ("user__email", "perfil__nombre")
    ordering = ("user",)

    # Filtrado por perfil del usuario logueado
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        user_perfil = getattr(request.user, 'user_perfil', None)
        return qs.filter(perfil=user_perfil) if user_perfil else qs.none()
