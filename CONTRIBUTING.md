# Environnement de développement

```bash
# https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
```

Créer un fichier `.env` à la racine du projet.

```
DEBUG=True
SECRET_KEY="django-insecure-z&aa%=c&ho$wsb*t7-zaiwt@_180^lp#52j*qcy^lif#mab74f"
ALLOWED_HOSTS=127.0.0.1,localhost
SITE_URL="http://127.0.0.1:8000"
```

# Initialisation de la base de données

```bash
cd src/
python manage.py migrate
# Mettre la même adresse e-mail la 2ème fois
# sinon cela bloque la création des utilisateurs
python manage.py createsuperuser
python manage.py create_global_settings
python manage.py create_club_groups
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
