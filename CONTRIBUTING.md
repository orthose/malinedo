# Environnement de développement

```bash
sudo apt install python3.11 python3.11-venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install pip-tools
pip-sync requirements-dev.txt
```

Créer un fichier `.env` à la racine du projet.

```
DEBUG=True
SECRET_KEY="django-insecure-z&aa%=c&ho$wsb*t7-zaiwt@_180^lp#52j*qcy^lif#mab74f"
ALLOWED_HOSTS=127.0.0.1,localhost
```

# Initialisation de la base de données

```bash
python manage.py migrate
# Mettre la même adresse e-mail la 2ème fois
# sinon cela bloque la création des utilisateurs
python manage.py createsuperuser
python manage.py create_global_settings
python manage.py create_club_groups
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
