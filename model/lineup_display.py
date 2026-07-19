# model/lineup_display.py

def render_pitch_svg(team_data: dict, primary_color: str) -> str:
    """
    Dibuja una cancha vertical con los jugadores posicionados según
    'line' (fila) y 'slot' (posición dentro de la fila) del JSON.
    GK abajo, delanteros arriba.
    """
    width, height = 304, 200
    max_line = max(p["line"] for p in team_data["players"])
    lines = {}
    for p in team_data["players"]:
        lines.setdefault(p["line"], []).append(p)

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0e3b1f" rx="8"/>',
        f'<line x1="0" y1="{height/2}" x2="{width}" y2="{height/2}" stroke="#ffffff33" stroke-width="1"/>',
        f'<circle cx="{width/2}" cy="{height/2}" r="25" fill="none" stroke="#ffffff33" stroke-width="1"/>',
    ]

    for line_num, players in lines.items():
        y = height - (line_num / (max_line + 0.5)) * height
        n = len(players)
        for i, p in enumerate(sorted(players, key=lambda x: x["slot"])):
            x = width * (i + 1) / (n + 1)
            svg_parts.append(
                f'<circle cx="{x}" cy="{y}" r="12" fill="{primary_color}" stroke="white" stroke-width="1.5"/>'
                f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="13" font-weight="700" fill="white">{p["number"]}</text>'
                f'<text x="{x}" y="{y+21}" text-anchor="middle" font-size="8" fill="white">{p["name"]}</text>'
            )

    svg_parts.append('</svg>')
    return "".join(svg_parts)

def render_lineups_stacked(home_data: dict, away_data: dict,
                            home_name: str, away_name: str,
                            home_color: str = "#AA151B",
                            away_color: str = "#75AADB"):
    """
    Layout vertical genérico: cancha del equipo local arriba, visitante abajo.
    Mobile-first, no asume Spain/Argentina.

    home_data / away_data: dict con {"formation": str, "players": [...]}
    home_name / away_name: nombre del equipo (viene de afuera, no del dict)
    home_color / away_color: color primario de cada camiseta (hex).
    """
    import streamlit as st

    st.markdown(f"**{home_name}** — {home_data['formation']}")
    st.markdown(render_pitch_svg(home_data, home_color), unsafe_allow_html=True)

    st.divider()

    st.markdown(f"**{away_name}** — {away_data['formation']}")
    st.markdown(render_pitch_svg(away_data, away_color), unsafe_allow_html=True)