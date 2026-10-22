#!/usr/bin/env bash
# Pasos de construcción en Render: dependencias, estáticos, tablas y datos de demostración.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py preparar_demo
