# Configuraciones de Optimización para settings.py
# Copiar estas configuraciones a tu archivo settings.py para máximo rendimiento

# ============================================================================
# OPTIMIZACIONES DE BASE DE DATOS
# ============================================================================

# Conexiones persistentes (reduce overhead de conexión)
DATABASES = {
    'default': {
        # ... tu configuración actual ...
        'CONN_MAX_AGE': 600,  # Mantener conexiones por 10 minutos
        'OPTIONS': {
            'connect_timeout': 10,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",  # Para MySQL
        },
    }
}

# ============================================================================
# CACHE (Opcional pero muy recomendado para 100k+ registros)
# ============================================================================

# Opción 1: Cache en memoria (desarrollo/testing)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'heladeria-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10000
        }
    }
}

# Opción 2: Redis (RECOMENDADO para producción)
# Primero instalar: pip install redis django-redis
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#             'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
#             'CONNECTION_POOL_KWARGS': {'max_connections': 50}
#         },
#         'KEY_PREFIX': 'heladeria',
#         'TIMEOUT': 300,  # 5 minutos por defecto
#     }
# }

# Cache para sesiones (mejora rendimiento significativamente)
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# ============================================================================
# OPTIMIZACIONES DE TEMPLATES
# ============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            # NUEVO: Cachear templates compilados
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ] if not DEBUG else [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

# ============================================================================
# OPTIMIZACIONES DE ARCHIVOS ESTÁTICOS
# ============================================================================

# Comprimir archivos estáticos (instalar: pip install django-compressor)
# INSTALLED_APPS += ['compressor']
# STATICFILES_FINDERS += ['compressor.finders.CompressorFinder']
# COMPRESS_ENABLED = True
# COMPRESS_OFFLINE = True  # Comprimir en deploy, no en runtime

# ============================================================================
# OPTIMIZACIONES DE MIDDLEWARE
# ============================================================================

# Habilitar caché de páginas completas (opcional, para páginas estáticas)
# MIDDLEWARE = [
#     'django.middleware.cache.UpdateCacheMiddleware',  # Primero
#     'django.middleware.common.CommonMiddleware',
#     # ... otros middleware ...
#     'django.middleware.cache.FetchFromCacheMiddleware',  # Último
# ]
# 
# CACHE_MIDDLEWARE_ALIAS = 'default'
# CACHE_MIDDLEWARE_SECONDS = 600  # 10 minutos
# CACHE_MIDDLEWARE_KEY_PREFIX = 'heladeria'

# ============================================================================
# SEGURIDAD Y RENDIMIENTO
# ============================================================================

# Aumentar timeout de requests
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# Optimizar sesiones
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_SAVE_EVERY_REQUEST = False  # No guardar sesión en cada request

# ============================================================================
# LOGGING PARA MONITOREO DE RENDIMIENTO
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file_slow_queries': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/slow_queries.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Logging de queries lentas (solo en desarrollo)
        'django.db.backends': {
            'handlers': ['file_slow_queries'] if DEBUG else [],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        # Logging de tu app
        'inventario': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================================
# VARIABLES DE ENTORNO (usar python-decouple)
# ============================================================================

# Instalar: pip install python-decouple
# from decouple import config, Csv
# 
# DEBUG = config('DEBUG', default=False, cast=bool)
# SECRET_KEY = config('SECRET_KEY')
# ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
# 
# # Base de datos desde variables de entorno
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='5432'),
#         'CONN_MAX_AGE': 600,
#     }
# }

# ============================================================================
# PAGINACIÓN GLOBAL
# ============================================================================

# Configuración por defecto para paginación
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
}

# ============================================================================
# MONITOREO (Producción)
# ============================================================================

# Django Debug Toolbar (solo desarrollo)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1', '::1']
    
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
        'ENABLE_STACKTRACES': True,
    }

# Sentry para tracking de errores (producción)
# Instalar: pip install sentry-sdk
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
# 
# if not DEBUG:
#     sentry_sdk.init(
#         dsn=config('SENTRY_DSN'),
#         integrations=[DjangoIntegration()],
#         traces_sample_rate=0.1,  # 10% de transacciones
#         send_default_pii=False,
#     )
