import streamlit as st

def apply():
    """Inyecta el tema oscuro Merme Bet en Streamlit.
    Llama esta funcion inmediatamente despues de st.set_page_config()."""
    st.markdown("""
        <style>
            /* Ocultar header y footer de Streamlit */
            header {visibility: hidden;}
            footer {visibility: hidden;}
            #stDecoration {display: none;}

            /* Fondo oscuro */
            .stApp {
                background-color: #09090b;
                color: #fafafa;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }

            /* Sidebar oscuro */
            section[data-testid="stSidebar"] {
                background-color: #09090b;
                border-right: 1px solid #27272a;
            }
            section[data-testid="stSidebar"] .stSidebarContent {
                color: #fafafa;
            }

            /* Contenedor principal */
            .main .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
                max-width: 1200px;
            }

            /* Tipografia */
            h1, h2, h3 {
                font-weight: 700;
                letter-spacing: -0.3px;
                color: #fafafa !important;
            }
            p, li, span, label {
                color: #e4e4e7;
            }

            /* Metricas */
            [data-testid="stMetricValue"] {
                font-size: 1.4rem;
                font-weight: 600;
                color: #fafafa;
            }
            [data-testid="stMetricLabel"] {
                font-size: 0.82rem;
                color: #a1a1aa;
            }

            /* Expanders */
            details {
                background-color: #18181b !important;
                border: 1px solid #27272a !important;
                border-radius: 8px !important;
            }
            details summary {
                color: #fafafa !important;
            }
            details summary:hover {
                color: #e4e4e7 !important;
            }

            /* Botones */
            .stButton button {
                background-color: #18181b;
                color: #fafafa;
                border: 1px solid #27272a;
                border-radius: 6px;
            }
            .stButton button:hover {
                background-color: #27272a;
                border-color: #3f3f46;
            }
            .stButton button:active {
                background-color: #3f3f46;
            }

            /* Selectbox / Inputs */
            .stSelectbox label, .stTextInput label, .stNumberInput label {
                color: #a1a1aa !important;
            }
            .stSelectbox div[data-baseweb="select"] > div,
            .stTextInput input,
            .stNumberInput input {
                background-color: #18181b !important;
                color: #fafafa !important;
                border: 1px solid #27272a !important;
                border-radius: 6px !important;
            }

            /* Tablas */
            .stDataFrame, [data-testid="stTable"] {
                background-color: #18181b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }

            /* Scrollbar */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #09090b;
            }
            ::-webkit-scrollbar-thumb {
                background: #27272a;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #3f3f46;
            }

            /* HR y caption */
            hr {
                margin: 1.1rem 0;
                opacity: 0.15;
                border-color: #27272a;
            }
            .stCaption, [data-testid="stCaption"] {
                color: #71717a !important;
            }

            /* Option menu / nav interno */
            div[data-testid="stSidebarNav"] {
                background-color: transparent;
            }
        </style>
    """, unsafe_allow_html=True)
