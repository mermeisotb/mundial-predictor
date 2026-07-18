import re
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from model.elo import calculate_elo_ratings
from model.poisson_model import predict_match
from model.h2h import calculate_h2h_probability
from model.corners_cards import get_team_averages, predict_corners_cards

DB_PATH = "data/db.sqlite"

TEAM_CODES = {
    "Argentina": "ar", "Brazil": "br", "France": "fr", "England": "gb-eng",
    "Spain": "es", "Germany": "de", "Portugal": "pt", "Netherlands": "nl",
    "Italy": "it", "Belgium": "be", "Uruguay": "uy", "Croatia": "hr",
    "Morocco": "ma", "Colombia": "co", "Mexico": "mx", "United States": "us",
    "Japan": "jp", "South Korea": "kr",
}

TEAM_COLORS = {
    "Argentina": "#75AADB", "Brazil": "#FFDF00", "France": "#0055A4",
    "England": "#CE1124", "Spain": "#C60B1E", "Germany": "#000000",
    "Portugal": "#006600", "Netherlands": "#FF6600", "Italy": "#0066CC",
    "Belgium": "#ED2939", "Uruguay": "#7B9ACC", "Croatia": "#FF0000",
    "Morocco": "#C1272D", "Colombia": "#FCD116", "Mexico": "#006341",
    "United States": "#3C3B6E", "Japan": "#BC002D", "South Korea": "#CD2E3A",
}
DEFAULT_COLOR = "#888888"

GOAL_MARKET_LINES = [1.5, 2.5, 3.5]
CORNER_MARKET_LINES = [5.5, 7.5, 9.5]
CARD_MARKET_LINES = [1.5, 2.5, 3.5]

st.set_page_config(page_title="Mundial Predictor", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
        /* Tipografía y espaciado general */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }
        h1, h2, h3 { font-weight: 700; letter-spacing: -0.3px; }
        [data-testid="stMetricValue"] { font-size: 1.4rem; }
        [data-testid="stMetricLabel"] { font-size: 0.82rem; opacity: 0.85; }

        /* Tarjetas (containers con borde) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px;
            background-color: rgba(255, 255, 255, 0.02);
        }

        /* Sidebar */
        section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.08); }

        /* Expanders más discretos */
        details {
            border-radius: 8px !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
        }

        hr { margin: 1.1rem 0; opacity: 0.15; }
    </style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers generales
# ---------------------------------------------------------------------------

def run_query(sql, params=()):
    """Ejecuta un SELECT y devuelve las filas; [] si la tabla no existe o falla."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows
    except sqlite3.OperationalError:
        return []


def team_flag_url(name):
    code = TEAM_CODES.get(name)
    return f"https://flagcdn.com/w80/{code}.png" if code else None


def team_color(name):
    return TEAM_COLORS.get(name, DEFAULT_COLOR)


def calcular_cuota_justa(probabilidad_porcentaje):
    """Convierte un porcentaje (ej: 47.2) en una cuota teórica (ej: 2.12)."""
    try:
        prob_decimal = probabilidad_porcentaje / 100.0
        return f"{round(1 / prob_decimal, 2):.2f}" if prob_decimal > 0 else "N/A"
    except ZeroDivisionError:
        return "N/A"


def normalizar_equipo(nombre):
    """Normaliza nombres para relacionar las distintas fuentes de datos."""
    aliases = {
        "usa": "united states",
        "united states of america": "united states",
        "korea republic": "south korea",
    }
    nombre_normalizado = re.sub(r"[^a-z0-9 ]", "", nombre.lower()).strip()
    return aliases.get(nombre_normalizado, nombre_normalizado)


def custom_bar(label, pct, color):
    st.markdown(f"""
        <div style="margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 2px;">
                <span>{label}</span>
                <span><b>{pct}%</b></span>
            </div>
            <div style="background-color: #333; border-radius: 4px; height: 10px;">
                <div style="background-color: {color}; width: {pct}%; height: 10px; border-radius: 4px;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)


@st.cache_data
def load_elo_ratings():
    return calculate_elo_ratings()


@st.cache_resource
def load_corner_card_averages():
    return get_team_averages()


# ---------------------------------------------------------------------------
# Acceso a datos
# ---------------------------------------------------------------------------

def get_prediction_features(home, away):
    """Busca la fila de kaggle_match_prediction_features para este cruce (en cualquier orden)."""
    rows = run_query("""
        SELECT * FROM kaggle_match_prediction_features
        WHERE (home_team_name = ? AND away_team_name = ?)
           OR (home_team_name = ? AND away_team_name = ?)
        ORDER BY date DESC LIMIT 1
    """, (home, away, away, home))
    if not rows:
        return None

    conn = sqlite3.connect(DB_PATH)
    columns = [c[1] for c in conn.execute("PRAGMA table_info(kaggle_match_prediction_features)")]
    conn.close()

    data = dict(zip(columns, rows[0]))
    swapped = data.get("home_team_name") != home

    def num(key):
        try:
            return float(data.get(key))
        except (TypeError, ValueError):
            return None

    def pick(local_key, visita_key):
        return (num(visita_key), num(local_key)) if swapped else (num(local_key), num(visita_key))

    return {
        "fifa_rank": pick("home_fifa_rank", "away_fifa_rank"),
        "elo_dataset": pick("home_elo", "away_elo"),
        "squad_avg_age": pick("home_squad_avg_age", "away_squad_avg_age"),
        "squad_total_caps": pick("home_squad_total_caps", "away_squad_total_caps"),
        "squad_total_value": pick("home_squad_total_value_eur", "away_squad_total_value_eur"),
        "rest_days": pick("home_rest_days", "away_rest_days"),
        "prev_avg_goals_scored": pick("home_prev_avg_goals_scored", "away_prev_avg_goals_scored"),
        "prev_avg_goals_conceded": pick("home_prev_avg_goals_conceded", "away_prev_avg_goals_conceded"),
        "prev_avg_possession": pick("home_prev_avg_possession", "away_prev_avg_possession"),
        "prev_avg_xg_scored": pick("home_prev_avg_xg_scored", "away_prev_avg_xg_scored"),
    }


def render_prediction_features(home, away):
    features = get_prediction_features(home, away)
    if not features:
        return

    with st.expander("📈 Datos avanzados (FIFA rank, Elo dataset, plantel y forma previa)"):
        st.caption("Fuente: FIFA World Cup 2026 Dataset (Kaggle) — match_prediction_features.")
        filas = [
            ("Ranking FIFA", features["fifa_rank"], "{:.0f}"),
            ("Elo (dataset)", features["elo_dataset"], "{:.0f}"),
            ("Edad promedio plantel", features["squad_avg_age"], "{:.1f} años"),
            ("Partidos internacionales (total)", features["squad_total_caps"], "{:.0f}"),
            ("Valor total plantel", features["squad_total_value"], "€{:,.0f}"),
            ("Días de descanso", features["rest_days"], "{:.0f}"),
            ("Goles a favor prom. (previos)", features["prev_avg_goals_scored"], "{:.2f}"),
            ("Goles en contra prom. (previos)", features["prev_avg_goals_conceded"], "{:.2f}"),
            ("Posesión prom. (previos)", features["prev_avg_possession"], "{:.1f}%"),
            ("xG a favor prom. (previos)", features["prev_avg_xg_scored"], "{:.2f}"),
        ]
        col_home, col_away = st.columns(2)
        col_home.markdown(f"**{home}**")
        col_away.markdown(f"**{away}**")
        for label, (v_home, v_away), fmt in filas:
            col_home.write(f"{label}: {fmt.format(v_home) if v_home is not None else '-'}")
            col_away.write(f"{label}: {fmt.format(v_away) if v_away is not None else '-'}")


def get_matches_for_analysis(include_finished=False):
    filtro_estado = "" if include_finished else "finished != 'TRUE' AND"
    return run_query(f"""
        SELECT id, local_date, stage, home_team, away_team, finished
        FROM worldcup26_matches
        WHERE {filtro_estado}
          home_team IS NOT NULL AND home_team != 'None' AND home_team != ''
          AND away_team IS NOT NULL AND away_team != 'None' AND away_team != ''
        ORDER BY local_date DESC
    """)


def get_pending_worldcup26_matches():
    """Cuenta partidos futuros cuyos equipos aún no están definidos."""
    rows = run_query("""
        SELECT COUNT(*) FROM worldcup26_matches
        WHERE finished != 'TRUE' AND (home_team IS NULL OR away_team IS NULL)
    """)
    return rows[0][0] if rows else 0


def get_worldcup26_results():
    return run_query("""
        SELECT home_team, away_team, home_score, away_score, group_name, stage, local_date, finished
        FROM worldcup26_matches
        WHERE finished = 'TRUE'
        ORDER BY local_date DESC
    """)


def obtener_cuotas_mercado(home, away):
    """Obtiene la última cuota disponible para el mismo cruce de selecciones."""
    rows = run_query("""
        SELECT home_team, away_team, odd_home, odd_draw, odd_away
        FROM match_odds
        WHERE home_team IS NOT NULL AND away_team IS NOT NULL
        ORDER BY last_update DESC
    """)
    home_normalizado = normalizar_equipo(home)
    away_normalizado = normalizar_equipo(away)
    for odds_home, odds_away, cuota_home, cuota_draw, cuota_away in rows:
        if (
            normalizar_equipo(odds_home) == home_normalizado
            and normalizar_equipo(odds_away) == away_normalizado
        ):
            return cuota_home, cuota_draw, cuota_away
    return None, None, None


def get_market_odds(tabla, home, away):
    """Devuelve todas las líneas over/under cargadas para un partido en una tabla dada."""
    rows = run_query(f"""
        SELECT line, odd_over, odd_under FROM {tabla}
        WHERE (home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?)
        ORDER BY line ASC
    """, (home, away, away, home))
    return rows


def get_market_odds_by_line(tabla, home, away):
    """Igual que get_market_odds pero indexado por línea, para lookup rápido."""
    return {line: (odd_over, odd_under) for line, odd_over, odd_under in get_market_odds(tabla, home, away)}


def get_btts_odds(home, away):
    rows = run_query("""
        SELECT odd_yes, odd_no FROM btts_odds
        WHERE (home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?)
    """, (home, away, away, home))
    return rows[0] if rows else (None, None)


def get_teams_with_players():
    return [r[0] for r in run_query("SELECT DISTINCT team_name FROM players ORDER BY team_name ASC")]


def get_players_by_team(team_name):
    return run_query("""
        SELECT player_name, position, club_team, market_value_eur, caps,
               matches_played, goals, assists, average_rating, minutes_played
        FROM players
        WHERE team_name = ?
        ORDER BY average_rating DESC, goals DESC
    """, (team_name,))


def get_active_teams():
    """Selecciones que todavía tienen partidos pendientes (no eliminadas)."""
    rows = run_query("""
        SELECT DISTINCT home_team FROM worldcup26_matches
        WHERE finished != 'TRUE' AND home_team IS NOT NULL AND home_team != 'None'
        UNION
        SELECT DISTINCT away_team FROM worldcup26_matches
        WHERE finished != 'TRUE' AND away_team IS NOT NULL AND away_team != 'None'
    """)
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Render: análisis de partido (usado por Predicciones)
# ---------------------------------------------------------------------------

def render_cuotas_mercado(home, away, prob_local, prob_empate, prob_visita,
                           cuota_local, cuota_empate, cuota_visita, show_missing_message=True):
    st.markdown("**Percepción del Mercado (Casas de Apuestas)**")

    if not cuota_local:
        if show_missing_message:
            st.info("Las cuotas reales aún no están disponibles en la API para este partido.")
            st.divider()
        return

    col1, col2, col3 = st.columns(3)
    datos = [
        (col1, f"🏠 {home} (Cuota: {cuota_local})", cuota_local, prob_local),
        (col2, f"🤝 Empate (Cuota: {cuota_empate})", cuota_empate, prob_empate),
        (col3, f"✈️ {away} (Cuota: {cuota_visita})", cuota_visita, prob_visita),
    ]
    for col, label, cuota, prob_modelo in datos:
        prob_mercado = (1 / cuota) * 100
        with col:
            st.metric(
                label=label,
                value=f"{prob_mercado:.1f}%",
                delta=f"{prob_modelo - prob_mercado:.1f}% vs Modelo",
            )
    st.divider()


def render_odds_comparison(home, away, poisson_result):
    st.subheader("Cuotas: modelo vs mercado")
    st.caption("La cuota teórica proviene del modelo Poisson; la cuota real se carga manualmente desde casas de apuestas (ej. Betano).")

    real_home, real_draw, real_away = obtener_cuotas_mercado(home, away)
    fair_odds = poisson_result["fair_odds"]

    columns = st.columns(3)
    outcomes = [(home, "home", real_home), ("Empate", "draw", real_draw), (away, "away", real_away)]
    for column, (label, outcome, real_odd) in zip(columns, outcomes):
        with column:
            fair_odd = fair_odds[outcome]
            if real_odd is None:
                st.metric(label, f"Teórica: {fair_odd:.2f}")
                st.caption("Cuota real pendiente")
            else:
                difference = ((real_odd / fair_odd) - 1) * 100
                st.metric(
                    label,
                    f"Teórica: {fair_odd:.2f}",
                    delta=f"Real: {real_odd:.2f} ({difference:+.1f}% vs modelo)",
                )
    st.divider()


def render_edge_metric(label, prob_modelo, odd_real):
    prob_mercado = (1 / odd_real) * 100
    edge = prob_modelo - prob_mercado
    st.metric(label, f"{prob_modelo:.1f}%", delta=f"Mercado: {prob_mercado:.1f}% · edge {edge:+.1f} pp")
    return edge


def render_market_group(titulo, icono, items):
    """items: lista de (label_linea, prob_modelo, odd_real_o_None).
    Devuelve lista de (nombre_completo, edge) para las líneas con cuota real."""
    st.markdown(f"**{icono} {titulo}**")
    cols = st.columns(len(items))
    edges = []
    for col, (label, prob_modelo, odd_real) in zip(cols, items):
        with col:
            if odd_real:
                edge = render_edge_metric(label, prob_modelo, odd_real)
                edges.append((f"{titulo} {label}", edge))
            else:
                st.metric(label, f"{prob_modelo}%")
                st.caption("Cuota real pendiente")
    return edges


def render_secondary_markets(home, away, poisson_result, corners_cards_result):
    st.subheader("Mercados")
    st.caption("Líneas agrupadas por categoría. Edge = diferencia entre la probabilidad del modelo y la implícita en la cuota real.")

    all_edges = []

    # --- Goles ---
    goals_by_line = get_market_odds_by_line("goals_odds", home, away)
    goal_items = [
        (f"+{line}", poisson_result["goal_lines"][line]["over_prob"], goals_by_line.get(line, (None, None))[0])
        for line in GOAL_MARKET_LINES
    ]
    all_edges += render_market_group("Goles", "⚽", goal_items)
    st.divider()

    # --- Córners ---
    corners_by_line = get_market_odds_by_line("corners_odds", home, away)
    corner_items = [
        (f"+{line}", corners_cards_result["corner_lines"][line]["over_prob"], corners_by_line.get(line, (None, None))[0])
        for line in CORNER_MARKET_LINES
    ]
    all_edges += render_market_group("Córners", "🚩", corner_items)
    st.divider()

    # --- Tarjetas ---
    cards_by_line = get_market_odds_by_line("cards_odds", home, away)
    card_items = [
        (f"+{line}", corners_cards_result["card_lines"][line]["over_prob"], cards_by_line.get(line, (None, None))[0])
        for line in CARD_MARKET_LINES
    ]
    all_edges += render_market_group("Tarjetas", "🟨", card_items)
    st.divider()

    # --- Ambos anotan ---
    st.markdown("**🤝 Ambos anotan**")
    odd_yes, _ = get_btts_odds(home, away)
    col = st.columns(1)[0]
    with col:
        if odd_yes:
            edge = render_edge_metric("Sí", poisson_result["btts_prob"], odd_yes)
            all_edges.append(("Ambos anotan", edge))
        else:
            st.metric("Sí", f"{poisson_result['btts_prob']}%")
            st.caption("Cuota real pendiente")
    st.divider()

    # --- Radar de valor: top 3 oportunidades ---
    top_edges = sorted(all_edges, key=lambda x: x[1], reverse=True)
    top_edges = [e for e in top_edges if e[1] >= 5][:3]
    if top_edges:
        st.markdown("**📈 Mejores oportunidades vs mercado**")
        for nombre, edge in top_edges:
            st.success(f"**{nombre}**: +{edge:.1f} puntos porcentuales sobre el mercado.")
        st.divider()

    # --- Líneas adicionales sin comparación de modelo (informativas) ---
    otras_lineas = []
    lineas_cubiertas = {
        "goals_odds": set(GOAL_MARKET_LINES),
        "corners_odds": set(CORNER_MARKET_LINES),
        "cards_odds": set(CARD_MARKET_LINES),
    }
    for tabla, nombre in [("goals_odds", "Goles"), ("corners_odds", "Córners"), ("cards_odds", "Tarjetas")]:
        rows = get_market_odds(tabla, home, away)
        for line, odd_over, odd_under in rows:
            if line not in lineas_cubiertas[tabla]:
                otras_lineas.append((nombre, line, odd_over, odd_under))

    if otras_lineas:
        with st.expander("Líneas adicionales de mercado (sin comparación de modelo)"):
            for nombre, line, odd_over, odd_under in otras_lineas:
                st.write(f"{nombre} {line}: Over {odd_over} / Under {odd_under}")

    st.divider()


def render_match_analysis(match_id, home, away, elo_ratings, corner_averages, show_odds_comparison=False):
    header_col1, header_col2, header_col3 = st.columns([1, 3, 1])
    with header_col1:
        flag = team_flag_url(home)
        if flag:
            st.image(flag, width=60)
    with header_col2:
        st.markdown(f"<h3 style='text-align: center;'>{home} vs {away}</h3>", unsafe_allow_html=True)
    with header_col3:
        flag = team_flag_url(away)
        if flag:
            st.image(flag, width=60)

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("**Elo (fuerza actual)**")
            st.metric(home, round(elo_ratings.get(home, 1500), 1))
            st.metric(away, round(elo_ratings.get(away, 1500), 1))

    poisson_result = predict_match(home, away)

    with col2:
        with st.container(border=True):
            st.markdown("**Predicción (Poisson)**")
            if poisson_result:
                fair = poisson_result["fair_odds"]
                custom_bar(f"🏠 Gana {home} (Cuota: {fair['home']})", poisson_result['home_win_prob'], team_color(home))
                custom_bar(f"🤝 Empate (Cuota: {fair['draw']})", poisson_result['draw_prob'], "#AAAAAA")
                custom_bar(f"✈️ Gana {away} (Cuota: {fair['away']})", poisson_result['away_win_prob'], team_color(away))

                st.divider()
                c1, c2 = st.columns(2)
                c1.metric("Ambos anotan", f"{poisson_result['btts_prob']}%")
                c2.metric("Mas de 2.5 goles", f"{poisson_result['over_2_5_prob']}%")
            else:
                st.write("Sin datos suficientes para calcular.")

    with col3:
        with st.container(border=True):
            st.markdown("**Corners y tarjetas (est. Mundial 2026)**")
            if corner_averages is None:
                st.info("⚠️ Estadísticas históricas de córners y tarjetas no disponibles en la base de datos.")
            else:
                try:
                    cc = predict_corners_cards(home, away, corner_averages)
                    st.write(f"Corners esperados: {cc['home_expected_corners']} ({home}) + {cc['away_expected_corners']} ({away}) = {cc['expected_corners']}")
                    st.write(f"Tarjetas amarillas esperadas: {cc['expected_cards']}")
                    st.write(f"Mas de 9.5 corners: {cc['over_9_5_corners_prob']}%")
                    st.write(f"Mas de 3.5 tarjetas: {cc['over_3_5_cards_prob']}%")
                    st.caption(cc['note'])
                except Exception:
                    st.info("⚠️ No se pudieron calcular estimaciones para este encuentro.")

    # 1) Cuotas con resultados (1X2: modelo vs mercado) — lo más importante primero
    if show_odds_comparison and poisson_result:
        render_odds_comparison(home, away, poisson_result)

    render_prediction_features(home, away)

    # 2) Mercados importantes, agrupados por categoría, con radar de valor
    if poisson_result:
        cc_result = predict_corners_cards(home, away, corner_averages) if corner_averages else None
        if cc_result:
            render_secondary_markets(home, away, poisson_result, cc_result)

    if poisson_result:
        c_local, c_empate, c_visita = obtener_cuotas_mercado(home, away)
        render_cuotas_mercado(
            home, away,
            poisson_result['home_win_prob'], poisson_result['draw_prob'], poisson_result['away_win_prob'],
            c_local, c_empate, c_visita,
        )

        st.markdown("**Marcadores mas probables**")
        scores_cols = st.columns(5)
        for i, (score, prob) in enumerate(poisson_result['top_scores']):
            with scores_cols[i]:
                cuota_marcador = calcular_cuota_justa(prob)
                st.markdown(f"""
                    <div style="text-align: center;">
                        <div style="font-size: 20px; color: #AAAAAA;">{prob}%</div>
                        <div style="font-size: 34px; font-weight: 700;">{score[0]}-{score[1]}</div>
                        <div style="font-size: 16px; color: #AAAAAA;">Cuota teórica: {cuota_marcador}</div>
                    </div>
                """, unsafe_allow_html=True)

    st.markdown("**Historial Head-to-Head**")
    h2h = calculate_h2h_probability(home, away)
    if not h2h["h2h_available"]:
        st.write(h2h["note"])
    else:
        st.write(
            f"Ultimos {h2h['matches_used']} enfrentamientos: "
            f"{h2h['wins_a']} victorias {home} ({h2h['prob_a_win_h2h']}%) | "
            f"{h2h['draws']} empates ({h2h['prob_draw_h2h']}%) | "
            f"{h2h['wins_b']} victorias {away} ({h2h['prob_b_win_h2h']}%)"
        )
        with st.expander("Ver historial detallado"):
            for h in h2h["history"]:
                st.write(h)

    st.divider()


# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------

def render_predictions_tab():
    st.title("Predicciones Estadísticas")
    st.caption(
        "Análisis impulsado por modelos Poisson y Ranking Elo. "
        "Incluye automáticamente los cruces de definición (3er puesto y final) cuando ya están confirmados."
    )

    incluir_finalizados = st.checkbox("Incluir partidos finalizados", value=False)
    matches = get_matches_for_analysis(include_finished=incluir_finalizados)

    if not matches:
        pending = get_pending_worldcup26_matches()
        if pending:
            st.info(
                "No hay partidos con selecciones definidas para analizar. "
                f"Quedan {pending} encuentro(s) pendientes de confirmar equipos. "
                "Actualiza con `py -3 data/fetch_worldcup26.py` cuando la fuente publique los cruces."
            )
        else:
            st.info("No hay partidos próximos en el calendario 2026. Actualiza con `py -3 data/fetch_worldcup26.py`.")
        return

    match_labels = {
        f"{m[3]} vs {m[4]} ({m[2]}) — {m[1][:10]}" + (" · Finalizado" if m[5] == "TRUE" else ""): m
        for m in matches
    }

    selected_labels = st.multiselect(
        "Selecciona los partidos a analizar:",
        options=list(match_labels.keys()),
        key="selector_partidos",
    )

    if st.button("Analizar seleccionados", type="primary"):
        if not selected_labels:
            st.info("Selecciona al menos un partido.")
            return
        with st.spinner("Ejecutando modelos..."):
            elo_ratings = load_elo_ratings()
            corner_averages = load_corner_card_averages()
            for label in selected_labels:
                match_id, _, stage, home, away, _ = match_labels[label]
                is_definitoria = stage in ("final", "third")
                render_match_analysis(
                    match_id, home, away, elo_ratings, corner_averages,
                    show_odds_comparison=is_definitoria,
                )


def render_players_tab():
    st.title("Jugadores")
    st.caption("Fuente: FIFA World Cup 2026 Dataset (Kaggle) — ratings, valor de mercado y stats por jugador.")

    teams = get_teams_with_players()
    if not teams:
        st.info("No hay datos de jugadores cargados. Ejecuta `python data/load_players.py`.")
        return

    active_teams = get_active_teams()
    solo_activos = st.checkbox("Mostrar solo selecciones aún en competencia", value=True)

    opciones = teams
    if solo_activos and active_teams:
        opciones = [t for t in teams if t in active_teams] or teams
        if opciones == teams:
            st.warning("No se detectaron selecciones activas todavía; mostrando todas.")

    equipo = st.selectbox("Selecciona una selección:", options=opciones)
    jugadores = get_players_by_team(equipo)

    if not jugadores:
        st.info("No hay jugadores cargados para esta selección.")
        return

    df = pd.DataFrame(jugadores, columns=[
        "Jugador", "Pos", "Club", "Valor de mercado (€)", "Partidos con selección",
        "PJ Mundial", "Goles", "Asistencias", "Rating prom.", "Minutos",
    ])
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor de mercado (€)": st.column_config.NumberColumn(format="€%d"),
            "Rating prom.": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def render_worldcup26_tab():
    st.title("Resultados del Mundial 2026")
    st.caption("Fuente: worldcup26.ir (datos oficiales del torneo en curso)")

    resultados = get_worldcup26_results()
    if not resultados:
        st.info("Todavia no hay partidos finalizados registrados. Ejecuta python data/fetch_worldcup26.py para actualizar.")
        return

    df = pd.DataFrame(resultados, columns=["Local", "Visitante", "GL", "GV", "Grupo", "Fase", "Fecha", "Finalizado"])
    df["Marcador"] = df["GL"].astype(str) + " - " + df["GV"].astype(str)
    df["Fase"] = df["Fase"].str.upper().fillna(df["Grupo"])

    fases_disponibles = sorted(df["Fase"].dropna().unique().tolist())
    fase_filtro = st.multiselect(
        "Filtrar por fase", options=fases_disponibles, default=fases_disponibles,
        key="filtro_fase_worldcup26",
    )

    df_filtrado = df[df["Fase"].isin(fase_filtro)][["Fecha", "Local", "Marcador", "Visitante", "Fase"]]
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    st.divider()
    st.caption(f"Ultima actualizacion de datos: {datetime.now().strftime('%d/%m/%Y %H:%M')}")


def render_footer():
    st.divider()
    with st.expander("ℹ️ Metodología, fuentes y créditos"):
        st.write("""
        *   **Datos Históricos:** football-data.org y API-Football.
        *   **Resultados en Vivo:** worldcup26.ir.
        *   **Jugadores:** FIFA World Cup 2026 Dataset (Kaggle).
        *   **Modelo:** Distribución de Poisson para los goles y Ranking Elo para la fuerza de cada selección.
        """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with st.sidebar:
        st.markdown(
            "<h2 style='text-align: center; margin-bottom: 0;'>🏆 Mundial Predictor</h2>"
            "<p style='text-align: center; opacity: 0.7; margin-top: 0.2rem;'>Panel de análisis 2026</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        menu_seleccionado = option_menu(
            menu_title=None,
            options=["Predicciones", "Jugadores", "Resultados Reales"],
            icons=["bar-chart-line", "people", "globe"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#00D26A", "font-size": "18px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#262730"},
                "nav-link-selected": {"background-color": "#1E1E1E", "color": "white"},
            }
        )

        st.divider()
        if st.button("🔄 Refrescar datos"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

        st.divider()
        st.caption("Datos: football-data.org · worldcup26.ir · Kaggle")

    if menu_seleccionado == "Predicciones":
        render_predictions_tab()
    elif menu_seleccionado == "Jugadores":
        render_players_tab()
    elif menu_seleccionado == "Resultados Reales":
        render_worldcup26_tab()

    render_footer()


if __name__ == "__main__":
    main()