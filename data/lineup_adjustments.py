"""
Ajustes manuales por bajas confirmadas (lesion, suspension, rotacion).
Edita este diccionario antes de cada partido con los jugadores que
NO van a jugar. El modelo resta su aporte ofensivo/defensivo real
(tomado de la tabla `players`) al lambda del equipo para ese cruce.

Formato:
    ("Equipo Local", "Equipo Visita"): {
        "Equipo Local": ["Nombre Jugador 1", "Nombre Jugador 2"],
        "Equipo Visita": ["Nombre Jugador 3"],
    }

Deja el diccionario vacio {} si no hay bajas confirmadas para ningun
partido, o simplemente no agregues la entrada para ese cruce.
"""

CONFIRMED_ABSENCES = {
    ("France", "England"): {
        # "France": ["Kylian Mbappe"],
        # "England": ["Bukayo Saka"],
    },
    ("Spain", "Argentina"): {
        # "Spain": [],
        # "Argentina": ["Lionel Messi"],
    },
}


def get_absences(home_team, away_team):
    """Devuelve el dict de bajas para este cruce (en cualquier orden), o {}."""
    direct = CONFIRMED_ABSENCES.get((home_team, away_team))
    if direct:
        return direct
    reverse = CONFIRMED_ABSENCES.get((away_team, home_team))
    return reverse or {}