import csv
import string
import secrets
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


def generate_random_password(length: int):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
        parser.add_argument(
            "--add-group",
            action="append",
            type=str,
            help="Association abréviation de groupe avec nom complet (ex: L=Loisir)",
        )

    def create_users(self, filename: str, mapping_groups: dict[str, str]):
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

                user = (
                    get_user_model()
                    .objects.filter(
                        username=row["Mail"],
                        first_name=row["Prénom"],
                        last_name=row["Nom"],
                    )
                    .first()
                )

                # On ne veut pas écraser les informations d'un utilisateur existant
                if not user:
                    try:
                        user = get_user_model().objects.create(
                            username=row["Mail"],
                            first_name=row["Prénom"],
                            last_name=row["Nom"],
                        )
                        user.set_password(generate_random_password(32))
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

                # Ajout des groupes
                if mapping_groups:
                    for short_name in row["Groupe"].split(","):
                        full_name = mapping_groups[short_name]
                        group = Group.objects.get(name=full_name)
                        user.groups.add(group)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{row['Prénom']} {row['Nom']} a été ajouté au groupe {full_name}"
                            )
                        )

    def handle(self, *args, **options):
        mapping_groups: dict[str, str] = dict()
        added_groups: list[str] | None = options["add_group"]
        if added_groups:
            for map_group in added_groups:
                short_name, full_name = map_group.split("=")
                assert Group.objects.filter(name=full_name).exists()
                mapping_groups[short_name] = full_name

        self.create_users(options["filename"], mapping_groups)
