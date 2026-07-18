#!/usr/bin/env bash
set -o errexit

echo "🚀 Iniciando proceso de construcción..."

# Instalar dependencias
echo "Instalando dependencias"
pip install -r requirements.txt

# Recopilar archivos estáticos
echo "Coleccionando archivos estáticos"
python manage.py collectstatic --noinput

# Aplicar migraciones
echo "Aplicando migraciones"
python manage.py migrate --noinput

# Crear superusuario (si no existe)
echo "👤 Creando superusuario..."

# Usar variables de entorno o valores por defecto
export DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME:-admin}
export DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@farmaciacfgos.com}
export DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-AdminPass123!}

# Este comando crea el superusuario sin pedir interacción
python manage.py createsuperuser --noinput || true

echo "✅ ¡Despliegue completado!"