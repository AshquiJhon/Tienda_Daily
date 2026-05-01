#!/usr/bin/env bash

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

echo "Creando superusuario..."

python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
import os;
username = 'admin';
password = '123456';
email = 'admin@gmail.com';
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
"