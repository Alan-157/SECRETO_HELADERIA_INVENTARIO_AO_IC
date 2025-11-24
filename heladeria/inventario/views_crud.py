# inventario/views_crud.py
from django.views.generic import ListView, CreateView, UpdateView, View
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from accounts.services import user_has_role



# ------------------------------
#   MIXIN PARA PERMISOS
# ------------------------------
class RoleRequiredMixin:
    allow = None         # Ej: ("Administrador", "Encargado")
    readonly_for = None  # Ej: ("Bodeguero",)

    def has_permission(self):
        user = self.request.user

        if user.is_superuser:
            return True

        if self.allow:
            if user_has_role(user, *self.allow):
                return True

        return False

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


# ------------------------------
#     LIST VIEW GENÉRICA
# ------------------------------
class RoleRequiredMixin:
    allow = None
    readonly_for = None

    def has_permission(self):
        user = self.request.user
        if user.is_superuser:
            return True
        if self.allow and user_has_role(user, *self.allow):
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class BaseListView(RoleRequiredMixin, ListView):
    template_name = ""
    partial_template = ""
    context_object_name = "items"
    search_fields = []
    order_default = "id"
    session_prefix = "list"

    # Puedes sobreescribir este mapa en cada List concreto
    sort_map = None  # ej: {"nombre":"nombre", "categoria":"categoria__nombre"}

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("per_page", 10)
        try:
            per_page = int(per_page)
            if per_page not in (5, 10, 20, 25, 50, 100):
                per_page = 10
        except:
            per_page = 10
        return per_page

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)

        # ---- BÚSQUEDA ----
        q = (self.request.GET.get("q") or "").strip()
        if q and self.search_fields:
            condiciones = Q()
            for f in self.search_fields:
                condiciones |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(condiciones)

        # ---- ORDEN NUEVO (sort + asc/desc) ----
        sort = (self.request.GET.get("sort") or "").strip()
        order_dir = (self.request.GET.get("order") or "").strip().lower()

        if self.sort_map and (sort or order_dir in ("asc", "desc")):
            sort_field = self.sort_map.get(sort, self.order_default)
            if order_dir == "desc":
                sort_field = f"-{sort_field}"
            qs = qs.order_by(sort_field)
            return qs

        # ---- ORDEN LEGACY (order=campo) ----
        order = self.request.GET.get("order")
        if not order:
            order = self.request.session.get(
                f"order_{self.session_prefix}",
                self.order_default
            )
        qs = qs.order_by(order)
        self.request.session[f"order_{self.session_prefix}"] = order
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        ctx["sort"] = (self.request.GET.get("sort") or "").strip()
        ctx["order"] = (self.request.GET.get("order") or "asc").strip()
        ctx["per_page"] = self.get_paginate_by(self.object_list)
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render(self.request, self.partial_template, context).content.decode("utf-8")
            return JsonResponse({"html": html})
        return super().render_to_response(context, **response_kwargs)

# ------------------------------
#   CREATE / UPDATE VIEWS
# ------------------------------
class BaseCreateView(RoleRequiredMixin, CreateView):
    template_name = "inventario/form.html"  # ✅ único template en inventario/
    titulo = ""
    success_url = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = self.titulo
        ctx["editar"] = False
        ctx["back_url"] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"{self.titulo} creado correctamente.")
        return super().form_valid(form)


class BaseUpdateView(RoleRequiredMixin, UpdateView):
    template_name = "inventario/form.html"  # ✅ único template en inventario/
    titulo = ""
    success_url = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = self.titulo
        ctx["editar"] = True
        ctx["back_url"] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"{self.titulo} actualizado correctamente.")
        return super().form_valid(form)
# ------------------------------
#        SOFT DELETE VIEW
# ------------------------------
class BaseSoftDeleteView(RoleRequiredMixin, View):
    model = None
    success_url = ""
    titulo = ""

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        messages.success(request, f"{self.titulo} fue ocultado correctamente.")
        return redirect(self.success_url)

    def get(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        return render(
            request,
            "crud/confirm_delete.html",
            {
                "obj": obj,
                "titulo": f"Ocultar {self.titulo}",
                "nota": "Esta eliminación NO borra el registro, solo lo oculta (is_active=False).",
            }
        )
