# SECRETO_HELADERIA_INVENTARIO_AO_IC
Inventario para Secreto Heladería  
Integrantes: **Alonzo Oviedo** e **Isaac Catalán**

## Descripción del Proyecto
Aplicación Django para gestión de inventario de insumos, lotes, movimientos y alertas para una heladería.

## Tecnologías Utilizadas
- Django 5.x
- MySQL / MariaDB
- Python 3.12
- HTML, CSS (en admin y frontend básico)

## Requisitos Previos
- Python 3.12+
- WAMPServer
- Git
- Visual Studio Code o tu IDE preferido

## Motor de base de datos
MySQL (administrado con WAMPServer)

## Clonar repositorio
git clone https://github.com/Alan-157/Secreto_Heladeria_Inventario.git


## Crear entorno virtual y activarlo
```bash
python -m venv venv
.\venv\Scripts\activate
```

## Instalar dependencias
pip install -r requirements.txt

## Configurar WAMP
> Abre WAMPServer y asegúrate de que esté en color verde (todos los servicios activos).
> Entra a phpMyAdmin (http://localhost/phpmyadmin).
> Crea una nueva base de datos llamada:
heladeria_bd (collation: utf8mb4_unicode_ci) 

## Crear archivo .env en la raíz del proyecto (ejemplo)
> **Importante:** No subas este archivo `.env` al repositorio público.  
> Contiene claves y contraseñas que deben mantenerse privadas.  
> Asegúrate de incluir `.env` en tu archivo `.gitignore` antes de subir el proyecto a GitHub.

```env
ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=
DB_ENGINE=django.db.backends.mysql
DB_NAME=heladeria
DB_USER=admin
DB_PASSWORD=Admin12345
DB_HOST=127.0.0.1
DB_PORT=3306
```
## Ejecutar migraciones y superusuario
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

## Cómo cargar las semillas
# Seed accounts
python manage.py seed_roles
python manage.py seed_admin
python manage.py seed_encargado
python manage.py seed_bodeguero
# Seed Inventario
python manage.py seed_categorias
python manage.py seed_insumos
python manage.py seed_bodegas
python manage.py seed_ubicaciones
python manage.py seed_lotes
python manage.py seed_ordenes
python manage.py seed_movimientos
python manage.py seed_alertas

## Ejecutar servidor local
python manage.py runserver

## Acceder a la aplicación
**Frontend:** [http://localhost:8000](http://localhost:8000)
**Panel de administración:** [http://localhost:8000/admin/](http://localhost:8000/admin/)

## Contribución
1. Haz un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature/nueva-funcionalidad`).
3. Haz tus cambios y confirma (`git commit -m "Agrega nueva funcionalidad"`).
4. Envía un Pull Request.

## Licencia
Este proyecto se distribuye bajo la licencia MIT.  
Consulta el archivo `LICENSE` para más detalles.