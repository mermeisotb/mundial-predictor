import streamlit as st
import sqlite3
import sys
import os

sys.path.append(os.path.dirname(__file__))

from model.elo import calculate_elo_ratings
from model.poisson_model import predict_match
from model.h2h import calculate_h2h_probability
from model.corners_cards import get_team_averages, predict_corners_cards

DB_PATH = "data/db.sqlite"

st.set_page_config(page_title="Mundial Predictor", layout="wide")


def get_upcoming_matches():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, utc_date, stage, home_team, away_team
        FROM matches
        WHERE status IN ('SCHEDULED', 'TIMED')
        ORDER BY utc_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


@st.cache_data
def load_elo_ratings():
    return calculate_elo_ratings()


@st.cache_data
def load_corner_card_averages():
    return get_team_averages()


def render_match_analysis(home, away, elo_ratings, corner_averages):
    st.subheader(f"⚽ {home} vs {away}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Elo (fuerza actual)**")
        elo_home = elo_ratings.get(home, 1500)
        elo_away = elo_ratings.get(away, 1500)
        st.metric(home, round(elo_home, 1))
        st.metric(away, round(elo_away, 1))

    poisson_result = predict_match(home, away)

    with col2:
        st.markdown("**Predicción (Poisson)**")
        if poisson_result:
            st.write(f"Gana {home}: **{poisson_result['home_win_prob']}%**")
            st.write(f"Empate: **{poisson_result['draw_prob']}%**")
            st.write(f"Gana {away}: **{poisson_result['away_win_prob']}%**")
            st.write(f"Ambos anotan: {poisson_result['btts_prob']}%")
            st.write(f"Más de 2.5 goles: {poisson_result['over_2_5_prob']}%")
        else:
            st.write("Sin datos suficientes para calcular.")

    with col3:
        st.markdown("**Córners y tarjetas (est. Mundial 2022)**")
        cc_result = predict_corners_cards(home, away, corner_averages)
        st.write(f"Córners esperados: {cc_result['expected_corners']}")
        st.write(f"Tarjetas amarillas esperadas: {cc_result['expected_cards']}")
        st.write(f"Más de 9.5 córners: {cc_result['over_9_5_corners_prob']}%")
        st.write(f"Más de 3.5 tarjetas: {cc_result['over_3_5_cards_prob']}%")
        st.caption(cc_result['note'])

    if poisson_result:
        st.markdown("**Marcadores más probables**")
        scores_cols = st.columns(5)
        for i, (score, prob) in enumerate(poisson_result['top_scores']):
            with scores_cols[i]:
                st.metric(f"{score[0]}-{score[1]}", f"{prob}%")

    st.markdown("**Historial Head-to-Head**")
    h2h = calculate_h2h_probability(home, away)
    if not h2h["h2h_available"]:
        st.write(h2h["note"])
    else:
        st.write(
            f"Últimos {h2h['matches_used']} enfrentamientos: "
            f"{h2h['wins_a']} victorias {home} ({h2h['prob_a_win_h2h']}%) | "
            f"{h2h['draws']} empates ({h2h['prob_draw_h2h']}%) | "
            f"{h2h['wins_b']} victorias {away} ({h2h['prob_b_win_h2h']}%)"
        )
        with st.expander("Ver historial detallado"):
            for h in h2h["history"]:
                st.write(h)

    st.divider()


def main():
    st.title("🏆 Mundial Predictor")
    st.caption("Análisis y probabilidades para partidos del Mundial — sin apuestas, solo investigación y práctica.")

    matches = get_upcoming_matches()

    if not matches:
        st.warning("No hay partidos próximos cargados. Corré `python data/fetch.py` para actualizar.")
        return

    match_labels = {
        f"{m[3]} vs {m[4]} ({m[2]}) — {m[1][:10]}": m for m in matches
    }

    selected_labels = st.multiselect(
        "Seleccioná los partidos a analizar (más partidos = más tiempo de cálculo):",
        options=list(match_labels.keys()),
    )

    if st.button("Analizar seleccionados", type="primary"):
        if not selected_labels:
            st.info("Seleccioná al menos un partido.")
            return

        with st.spinner("Calculando..."):
            elo_ratings = load_elo_ratings()
            corner_averages = load_corner_card_averages()

        for label in selected_labels:
            match = match_labels[label]
            home, away = match[3], match[4]
            render_match_analysis(home, away, elo_ratings, corner_averages)


if __name__ == "__main__":
    main()