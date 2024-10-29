# Environnement de développement

```bash
sudo apt install python3.11 python3.11-venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install pip-tools
pip-sync requirements-dev.txt
```

# Initialisation de la base de données

```bash
python manage.py migrate
# Mettre la même adresse e-mail la 2ème fois
# sinon cela bloque la création des utilisateurs
python manage.py createsuperuser
python manage.py create_global_settings
python manage.py create_club_groups
python manage.py create_sessions_2024
python manage.py create_users users.csv
python manage.py create_users --add-group groups.csv
```

# Modification des modèles

```bash
python manage.py makemigrations
python manage.py migrate
```

# Lancement du serveur

```bash
python manage.py runserver
```

# Formatage du code

```bash
ruff format
ruff check
```
