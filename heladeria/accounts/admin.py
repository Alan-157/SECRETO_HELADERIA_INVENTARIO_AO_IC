from django.contrib import admin, messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import UserPerfil, UsuarioApp, UserPerfilAsignacion
from .services import activar_asignacion
from django.utils.html import format_html


# --- ACCIONES COMUNES ---

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


# --- ACCIONES PARA ASIGNACIONES (NUEVAS) ---

@admin.action(description="Finalizar asignaciones seleccionadas (cerrar vigencia)")
def finalizar_asignaciones(modeladmin, request, queryset):
    n = 0
    for asignacion in queryset:
        if asignacion.ended_at is None:
            asignacion.ended_at = timezone.now()
            asignacion.save(update_fields=["ended_at"])
            # si es la activa del usuario, borrar puntero
            user = asignacion.user
            if user.active_asignacion_id == asignacion.id:
                user.active_asignacion = None
                user.save(update_fields=["active_asignacion"])
            n += 1
    modeladmin.message_user(request, f"{n} asignación(es) finalizada(s).", messages.INFO)


@admin.action(description="Marcar asignaciones como vigentes (finaliza otras)")
def hacer_vigente(modeladmin, request, queryset):
    for asignacion in queryset:
        activar_asignacion(asignacion.user, asignacion.perfil)
    modeladmin.message_user(request, "Asignación(es) marcada(s) como vigente(s).", messages.SUCCESS)


# --- INLINE (opcional: ver asignaciones dentro del Perfil) ---

class UserPerfilAsignacionInline(admin.TabularInline):
    model = UserPerfilAsignacion
    extra = 0
    fields = ("user", "started_at", "ended_at")
    readonly_fields = ("started_at", "ended_at")
    show_change_link = True
    verbose_name = "Asignación de usuario"
    verbose_name_plural = "Asignaciones de usuarios"


# --- ADMIN: UserPerfil ---

@admin.register(UserPerfil)
class UserPerfilAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("nombre",)
    ordering = ("nombre",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [UserPerfilAsignacionInline]
    actions = [activar_perfiles, desactivar_perfiles]

    def has_module_permission(self, request):
        # Solo superusuario ve este módulo (puedes abrirlo a 'admin' si lo deseas)
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        # Validar que no exista otra asignación vigente del mismo user
        vigente = UserPerfilAsignacion.objects.filter(
            user=obj.user, ended_at__isnull=True
        ).exclude(id=obj.id)
        if vigente.exists():
            raise ValidationError("El usuario ya tiene una asignación vigente.")
        super().save_model(request, obj, form, change)


# --- ADMIN: UsuarioApp ---

@admin.register(UsuarioApp)
class UsuarioAppAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name","phone","avatar_thumb","is_active", "active_asignacion", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("email", "name")
    ordering = ("email",)
    readonly_fields = ("created_at", "updated_at", "active_asignacion","avatar_thumb")
    actions = [activar_usuarios, desactivar_usuarios]

    def avatar_thumb(self, obj):
        if getattr(obj, "avatar", None):
            return format_html('<img src="{}" style="height:48px;width:48px;object-fit:cover;border-radius:50%;">', obj.avatar.url)
        return "—"
    avatar_thumb.short_description = "Foto"

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# --- ADMIN: UserPerfilAsignacion ---

@admin.register(UserPerfilAsignacion)
class UserPerfilAsignacionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "perfil", "started_at", "ended_at", "vigente")
    list_filter = ("perfil", "ended_at")
    search_fields = ("user__email", "perfil__nombre")
    ordering = ("user",)
    actions = [finalizar_asignaciones, hacer_vigente]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # superusuario ve todo; otros podrían limitarse a sus perfiles si lo implementas
        if request.user.is_superuser:
            return qs
        return qs.none()
