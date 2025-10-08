from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
# Importamos los modelos base (ya refactorizados para BaseModel en la guía)
from .models import Rol, UserPerfil, UsuarioApp, UserPerfilAsignacion 

# --- ACCIONES PERSONALIZADAS: Activar/Desactivar (Clase U2 C3) ---

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
# Usamos el formset avanzado para incluir validaciones como en tu código original
class AsignacionInlineFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # [Implementación de la validación]
        # Aquí iría tu lógica original para validar duplicados o estado inactivo.
        # Por ejemplo: raise ValidationError("Cada usuario puede tener solo una asignación ACTIVA en este perfil.")
        # La incluimos como referencia para el aprendizaje de validaciones avanzadas (Clase U2 C3).
        pass

class UserPerfilAsignacionInline(admin.TabularInline):
    model = UserPerfilAsignacion
    formset = AsignacionInlineFormset
    extra = 0
    fields = ("user", "activo", "assigned_at")
    readonly_fields = ("assigned_at",)
    show_change_link = True


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


@admin.register(UsuarioApp)
class UsuarioAppAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name", "rol", "user_perfil", "is_active", "updated_at")
    # Filtra por estado (is_active), perfil y rol
    list_filter = ("is_active", "user_perfil", "rol") 
    search_fields = ("email", "name", "user_perfil__nombre", "rol__nombre") # Búsqueda por FK
    ordering = ("email",)
    readonly_fields = ("created_at", "updated_at")
    actions = [activar_usuarios, desactivar_usuarios]


@admin.register(UserPerfilAsignacion)
class UserPerfilAsignacionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "perfil", "activo", "assigned_at")
    list_filter = ("activo", "perfil")
    search_fields = ("user__email", "perfil__nombre")
    ordering = ("user",)
