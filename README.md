# Description

*MaLineDo* est l'application web de réservation des créneaux d'entraînement 
pour le club de nage avec palmes de l'USPalaiseau.

Afin de garantir le bon fonctionnement du club, nous devons nous assurer que le taux d'utilisation des lignes d'eau qui nous sont allouées soit le plus important possible.

*MaLineDo* a été conçue dans le but de simplifier le processus de réservation des créneaux, en permettant un suivi efficace des inscriptions des nageurs aux séances disponibles. Le tout en automatisant le plus possible le processus de réservation.

Ainsi, *MaLineDo* n'est pas une application de réservation classique. En effet, son mode de fonctionnement est inversé. Contrairement aux applications de réservation classiques, vous n'avez pas besoin de confirmer votre présence à une séance. La plupart du temps, vous n'aurez absolument rien à faire dans l'application, sauf en cas de désistement. 

# Installation et configuration

L'application a été développée sous Ubuntu 22.04.
Les instructions ci-après ont été testées sous Debian 12.
Je me suis inspiré de ce [tutoriel](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu).

## Installation des composants

```bash
sudo apt update && sudo apt upgrade
sudo apt install python3.11 python3.11-venv postgresql postgresql-client nginx git cron
```

## Base de données

```bash
sudo -u postgres psql
CREATE DATABASE malinedodb;
CREATE USER malinedo WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE malinedodb TO malinedo;
ALTER DATABASE malinedodb OWNER TO malinedo;
```

## Téléchargement du projet

```bash
# Création d'un utilisateur applicatif sans droits sudo
sudo useradd -s /bin/bash -m malinedo
sudo usermod -a -G www-data malinedo
sudo mkdir /var/www/html/malinedo
sudo chmod 750 /var/www/html/malinedo
sudo chown malinedo:www-data /var/www/html/malinedo
sudo su malinedo
cd /home/malinedo
git clone https://github.com/orthose/malinedo.git
cd malinedo
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-prod.txt
```

## Variables d'environnement

```bash
touch config.sh
chmod 700 config.sh
nano config.sh
```

```bash
export DJANGO_SETTINGS_MODULE=malinedo.settings-prod

export ALLOWED_HOSTS=127.0.0.1,localhost,domaine.com

export ADMIN_URL=admin/ 
export STATIC_ROOT=/var/www/html/malinedo/static/

export DATABASE_NAME=malinedodb
export DATABASE_USER=malinedo
export DATABASE_PASSWORD=password
export DATABASE_HOST=localhost
export DATABASE_PORT=5432

export EMAIL_HOST=smtp.example.com
export EMAIL_PORT=1
export EMAIL_USE_TLS=true
export EMAIL_HOST_USER=contact@domaine.com
export EMAIL_HOST_PASSWORD=password
export EMAIL_USE_SSL=false
export DEFAULT_FROM_EMAIL=ne-pas-repondre@domaine.com
```

## Tâches planifiées

CRON close_registrations, postgre dump

```bash
mkdir ~/backup
chmod 700 ~/backup
crontab -e
```

```
0 1 * * sat cd ~/malinedo && source config.sh && .venv/bin/python manage.py close_registrations
@daily pg_dump -U malinedo malinedodb > ~/backup/malinedodb_$(date +\%F).sql
```

## Initialisation des données

```bash
source config.sh
python manage.py migrate
# Mettre la même adresse e-mail la 2ème fois
# sinon cela bloque la création des utilisateurs
python manage.py createsuperuser
python manage.py create_global_settings
python manage.py create_club_groups
python manage.py create_sessions_2024
python manage.py create_users users.csv
python manage.py create_users --add-group groups.csv
python manage.py collectstatic
```

## Création du service

```bash
sudo nano /etc/systemd/system/malinedo.service
```

Le nombre de workers recommandé est (2 * CPU) + 1.

```
[Unit]
Description=Application de réservation de créneaux
After=network.target

[Service]
User=malinedo
Group=malinedo
WorkingDirectory=/home/malinedo/malinedo/
ExecStart=/bin/bash -c "source config.sh && .venv/bin/gunicorn --access-logfile - --bind 127.0.0.1:8000 --workers 3 malinedo.wsgi:application"
ExecStop=/bin/kill -SIGINT $MAINPID
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl start malinedo
sudo systemctl status malinedo
```

## Serveur Nginx

```bash
cd /etc/nginx/sites-available
ln -s /etc/nginx/sites-available/html /etc/nginx/sites-enabled/html
sudo nano html
```

```
# Redirection HTTP -> HTTPS
server {
	listen 80;
    listen [::]:80;
	server_name domaine.com *.domaine.com;
	return 301 https://$server_name$request_uri;
}

server {
	listen 443 ssl http2;
	listen [::]:443 ssl http2;

    server_name domaine.com;
	server_tokens off;	

	# Certificat SSL
	ssl_certificate /certs/bundle.cer;
    ssl_certificate_key /certs/domaine.com_private_key.key;
    #ssl_trusted_certificate /certs/domaine.com_ssl_certificate_INTERMEDIATE.cer;
	ssl_dhparam /etc/ssl/certs/dhparam.pem;
	ssl_protocols TLSv1.2 TLSv1.3;
	ssl_ciphers ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-CCM:DHE-RSA-AES256-CCM8:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-CCM:DHE-RSA-AES128-CCM8:DHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256;
	ssl_prefer_server_ciphers on;
	ssl_session_tickets off;
	ssl_session_timeout 1d;
	ssl_session_cache shared:SSL:10m;
	ssl_buffer_size 8k;
	ssl_stapling on;
	ssl_stapling_verify on;
    
    location /favicon.ico {
		alias /var/www/html/malinedo/static/img/favicon.ico;
	}

	location /static/ {
	    root /var/www/html/malinedo/static/;
	}

	location / {
	    include proxy_params;
		proxy_pass http://127.0.0.1:8000;
	}
}
```

```bash
sudo nginx -t
sudo systemctl restart nginx
```

# Utilisation

## Première connexion

Accédez au site via l'URL https://domaine.com/.
Entrez votre adresse email. Le mot de passe par défaut 
est le prénom en minuscule de l'adhérent.

Lors de votre première connexion modifiez votre mot de passe
en cliquant sur **Profil**.

## Attribution des groupes

Les groupes disponibles sont :
* Bureau: Ajoute le lien vers l'interface d'administration dans la barre de navigation.
* Entraîneur: Permet de s'inscrire en tant qu'entraîneur aux séances. 
* Loisir: Permet de s'inscrire aux séances de loisir.
* Jeune: Permet de s'inscrire aux séances de compétition pour les jeunes.
* Compétition N1: Permet de s'inscrire aux séances pour les compétiteurs classiques.
* Compétition N2: Permet de s'inscrire aux séances pour les compétiteurs confirmés.

Accédez à l'interface administrateur via l'URL https://domaine.com/<ADMIN_URL>/.
La variable `ADMIN_URL` ayant été définie dans `config.sh`.

Commencez par cliquer sur **Utilisateurs** et donnez les accès aux membres du bureau.
Pour cela cliquez sur l'utilisateur, ajoutez-lui le groupe **Bureau**
et cochez **Statut équipe**. Généralement un membre du bureau voudra voir tous les
créneaux disponibles, donc il faudra l'ajouter dans tous les groupes.
N'oubliez pas de cliquer sur **Enregistrer** tout en bas.

Ensuite, pour chaque utilisateur ajoutez-le dans les groupes dont il a besoin.
