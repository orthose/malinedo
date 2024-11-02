class ClubGroup:
    BOARD = "Bureau"
    COACH = "Entraîneur"
    LEISURE = "Loisir"
    YOUNG = "Jeune"  # Jeunes compétiteurs
    COMPET_N1 = "Compétition N1"  # Compétiteurs classiques
    COMPET_N2 = "Compétition N2"  # Compétiteurs confirmés


class RegisterPermission:
    COACH = "register_coach_session"
    LEISURE = "register_leisure_session"
    YOUNG = "register_young_session"
    COMPET_N1 = "register_competn1_session"
    COMPET_N2 = "register_competn2_session"

    @classmethod
    def get_perm(cls, group: str) -> str | None:
        match group:
            case "L":
                return "booking." + cls.LEISURE

            case "J":
                return "booking." + cls.YOUNG

            case "C1":
                return "booking." + cls.COMPET_N1

            case "C2":
                return "booking." + cls.COMPET_N2

        return None