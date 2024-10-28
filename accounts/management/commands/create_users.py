import csv
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from booking.models import ClubGroup


class Command(BaseCommand):
    """
    Crée les utilisateurs à partir d'un fichier CSV
    Assigne les groupes aux utilisateurs à partir d'un autre fichier CSV

    Les noms de colonne attendus sont :
        + Prénom
        + Nom
        + Mail
        + Groupe

    Modifiez les noms de colonne du CSV en conséquence
    """

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)
        parser.add_argument("--add-group", action="store_true", default=False)

    def create_users(self, filename: str):
        with open(filename, mode="r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")

            for row in reader:
                if row["Prénom"] == "" or row["Nom"] == "":
                    continue

                # Nettoyage des données
                row["Prénom"] = row["Prénom"].strip()
                row["Nom"] = row["Nom"].strip()
                row["Mail"] = row["Mail"].strip()

                if row["Mail"] == "":
                    self.stdout.write(
                        self.style.ERROR(
                            f"{row['Prénom']} {row['Nom']} n'a pas de mail renseigné"
                        )
                    )
                    continue

                user_exists = (
                    get_user_model()
                    .objects.filter(
                        username=row["Mail"],
                        first_name=row["Prénom"],
                        last_name=row["Nom"],
                    )
                    .exists()
                )

                # On ne veut pas écraser les informations d'un utilisateur existant
                if not user_exists:
                    try:
                        user = get_user_model().objects.create(
                            username=row["Mail"],
                            first_name=row["Prénom"],
                            last_name=row["Nom"],
                        )
                        user.set_password(row["Prénom"].lower())
                        user.save()

                    except IntegrityError as error:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Le mail {row['Mail']} de {row['Prénom']} {row['Nom']} existe déjà"
                            )
                        )
                        self.stdout.write(self.style.ERROR(error))
                        continue

                    self.stdout.write(
                        self.style.SUCCESS(f"{row['Prénom']} {row['Nom']} a été ajouté")
                    )

    def add_group(self, filename: str):
        young_group = Group.objects.get(name=ClubGroup.YOUNG)
        leisure_group = Group.objects.get(name=ClubGroup.LEISURE)
        competn1_group = Group.objects.get(name=ClubGroup.COMPET_N1)
        competn2_group = Group.objects.get(name=ClubGroup.COMPET_N2)

        with open(filename, mode="r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")

            for row in reader:
                if row["Prénom"] == "" or row["Nom"] == "":
                    continue

                # Nettoyage des données
                row["Prénom"] = row["Prénom"].strip()
                row["Nom"] = row["Nom"].strip()
                row["Groupe"] = row["Groupe"].strip().upper()

                try:
                    user = get_user_model().objects.get(
                        first_name=row["Prénom"],
                        last_name=row["Nom"],
                    )
                except get_user_model().DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"{row['Prénom']} {row['Nom']} n'est pas enregistré"
                        )
                    )
                    continue

                match row["Groupe"]:
                    case "L":
                        user.groups.add(leisure_group)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{row['Prénom']} {row['Nom']} a été ajouté aux groupe de loisir"
                            )
                        )
                    case "C":
                        user.groups.add(
                            young_group,
                            competn1_group,
                            competn2_group,
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{row['Prénom']} {row['Nom']} a été ajouté aux groupes de compétition"
                            )
                        )
                    case _:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Le groupe de {row['Prénom']} {row['Nom']} n'est pas renseigné"
                            )
                        )

    def handle(self, *args, **options):
        if not options["add_group"]:
            self.create_users(options["filename"])
        else:
            self.add_group(options["filename"])
