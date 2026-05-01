#!/usr/bin/env bash

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

echo "CREANDO SUPERUSUARIO..."

python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); import os; username='admin'; password='123456'; email='admin@gmail.com'; User.objects.filter(username=username).exists() or User.objects.create_superuser(username, email, password)"