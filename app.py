# =============================================================================
# FTBL7 LABS — app.py
# Entry point: sidebar navigasi 5 modul
# Jalankan: streamlit run app.py
# =============================================================================

import streamlit as st
from modules.clip_detector import render as render_clip_detector

# ── Page config (WAJIB baris pertama) ────────────────────────────────────────
st.set_page_config(
    page_title="FTBL7 Labs",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── CSS Dark Mode ─────────────────────────────────────────────────────────────
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0d0f14 !important;
        font-family: 'Inter', sans-serif;
        color: #e8eaf0;
    }
    [data-testid="stSidebar"] {
        background-color: #13161e !important;
        border-right: 1px solid #252a38;
    }
    [data-testid="stHeader"] {
        background-color: #0d0f14 !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff, #0099bb) !important;
        color: #000 !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar() -> str:
    with st.sidebar:
        # Brand
        st.markdown("""
        <div style="text-align:center; padding: 0.5rem 0 1.5rem;">
            <div style="font-size:2.5rem;">⚽</div>
            <div style="font-size:1.1rem; font-weight:700; color:#e8eaf0;">FTBL7 LABS</div>
            <div style="font-size:0.7rem; color:#8892a4; letter-spacing:0.1em; text-transform:uppercase;">Content Intelligence</div>
        </div>
        <hr style="border-color:#252a38; margin:0 0 1rem;">
        """, unsafe_allow_html=True)

        # 5 Menu Navigasi
        menu = st.radio(
            label="",
            options=[
                "🏠  Home",
                "🎬  Clip Detector",
                "📊  Trend & Sentiment",
                "🔍  SEO Optimizer",
                "✍️  Content Reviewer",
            ],
            label_visibility="collapsed",
        )

        st.markdown('<hr style="border-color:#252a38; margin:1.5rem 0 1rem;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.7rem;color:#4a5568;text-align:center;">v1.0.0 · Powered by Gemini</div>', unsafe_allow_html=True)

        return menu


# ── Placeholder per halaman ───────────────────────────────────────────────────
def page_home():
    st.title("🏠 Home")
    st.info("Dashboard overview — coming soon.")

def page_clip_detector():
    render_clip_detector()

def page_trend_sentiment():
    st.title("📊 Trend & Sentiment")
    st.info("Modul ini akan menganalisis tren dan sentimen.")

def page_seo_optimizer():
    st.title("🔍 SEO Optimizer")
    st.info("Modul ini akan mengoptimasi judul, hashtag, dan deskripsi.")

def page_content_reviewer():
    st.title("✍️ Content Reviewer")
    st.info("Modul ini akan mereview naskah dan caption sebelum tayang.")


# ── Router ────────────────────────────────────────────────────────────────────
ROUTES = {
    "🏠  Home":              page_home,
    "🎬  Clip Detector":     page_clip_detector,
    "📊  Trend & Sentiment": page_trend_sentiment,
    "🔍  SEO Optimizer":     page_seo_optimizer,
    "✍️  Content Reviewer":  page_content_reviewer,
}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    load_css()
    active = render_sidebar()
    ROUTES[active]()


if __name__ == "__main__":
    main()
