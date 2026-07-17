#!/usr/bin/env bash

set -o errexit
echo "Fallo en el despliegue"


echo "Instalando dependencias"
pip install -r requirements.txt

echo "Recopilando archivos estáticos"
python manage.py collectstatic --no-input

echo "Aplicando migraciones...."
python manage.py migrate --no-input

echo "Despliegue completado"