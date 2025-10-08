# heladeria/accounts/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm # Importa el formulario que creaste
from django.contrib.auth import login # Opcional: si quieres loguear al usuario inmediatamente después del registro

# NOTA: La vista de login (LoginView) no está aquí, está en urls.py

def register_view(request):
    """
    Vista de función para el registro de nuevos usuarios.
    Maneja el envío del formulario (POST) y la visualización (GET).
    """
    if request.method == 'POST':
        # 1. Procesa la data del formulario
        form = RegisterForm(request.POST)
        
        if form.is_valid():
            # 2. Si es válido, guarda el usuario
            user = form.save()
            
            # 3. Muestra un mensaje de éxito y redirige
            messages.success(request, '¡Cuenta creada con éxito! Ahora puedes iniciar sesión.')
            
            # Si deseas que el usuario inicie sesión inmediatamente:
            # login(request, user)
            
            # Redirige a la vista de login (usando el 'name' definido en accounts/urls.py)
            return redirect('accounts:login') 
        else:
            # Si hay errores (ej. contraseñas no coinciden), el formulario (form)
            # se pasa al contexto para que el template muestre los errores.
            pass
    else:
        # 4. Petición GET: muestra un formulario vacío
        form = RegisterForm()
    
    # Renderiza el template, utilizando la ruta simplificada
    return render(request, "accounts/register.html", {"form": form})
