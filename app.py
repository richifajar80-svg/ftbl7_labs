# =============================================================================
# FTBL7 LABS — app.py  |  Entry point + Global CSS
# =============================================================================

import base64
import streamlit as st
from modules.clip_detector import render as render_clip_detector


# ── SVG logo as base64 data URI (bypass Streamlit HTML sanitizer) ─────────────
def _logo_img(size: int = 64) -> str:
    """Return <img> tag with circuit-cross logo embedded as base64 SVG."""
    svg = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="g" x="-70%" y="-70%" width="240%" height="240%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="b1"/>
      <feGaussianBlur in="SourceGraphic" stdDeviation="8"   result="b2"/>
      <feGaussianBlur in="SourceGraphic" stdDeviation="1.2" result="b3"/>
      <feMerge>
        <feMergeNode in="b2"/>
        <feMergeNode in="b1"/>
        <feMergeNode in="b3"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <linearGradient id="gr" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%"   stop-color="#00e5ff"/>
      <stop offset="55%"  stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#3b82f6"/>
    </linearGradient>
  </defs>
  <g filter="url(#g)">
    <g stroke="url(#gr)" stroke-width="4" stroke-linecap="round"
       stroke-linejoin="round" fill="none">
      <!-- Top horizontal bar -->
      <line x1="28" y1="20" x2="72" y2="20"/>
      <!-- Vertical stem: top-bar centre → cross centre -->
      <line x1="50" y1="20" x2="50" y2="50"/>
      <!-- Left arm -->
      <line x1="50" y1="50" x2="18" y2="50"/>
      <!-- Right arm -->
      <line x1="50" y1="50" x2="82" y2="50"/>
      <!-- Bottom-left branch: centre → down junction → left → down -->
      <polyline points="50,50 50,66 28,66 28,80"/>
      <!-- Bottom-right branch: down junction → right → down -->
      <polyline points="50,66 72,66 72,80"/>
    </g>
    <g fill="url(#gr)">
      <!-- Top bar nodes -->
      <circle cx="28" cy="20" r="5"/>
      <circle cx="72" cy="20" r="5"/>
      <!-- Side nodes -->
      <circle cx="18" cy="50" r="5"/>
      <circle cx="82" cy="50" r="5"/>
      <!-- Bottom nodes -->
      <circle cx="28" cy="80" r="5"/>
      <circle cx="72" cy="80" r="5"/>
    </g>
  </g>
</svg>"""
    b64 = base64.b64encode(svg.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{size}" height="{size}" style="overflow:visible; display:block;">'

st.set_page_config(
    page_title="FTBL7 Labs",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Global CSS (deep navy modern — inspired by 2short.ai) ────────────────────
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Design tokens ── */
    :root {
        --navy-900: #060b18;
        --navy-800: #0b1120;
        --navy-700: #0f1729;
        --navy-600: #141e35;
        --navy-500: #1a2640;
        --navy-400: #243050;
        --navy-300: #2e3d62;
        --blue-500: #3b82f6;
        --blue-400: #60a5fa;
        --blue-300: #93c5fd;
        --blue-glow: rgba(59,130,246,0.25);
        --text-100: #f0f4ff;
        --text-200: #c8d3ea;
        --text-400: #7a8fba;
        --text-600: #4a5878;
        --border:   rgba(59,130,246,0.12);
        --border-hover: rgba(59,130,246,0.35);
        --radius-lg: 16px;
        --radius-md: 12px;
        --radius-sm: 8px;
        --shadow: 0 4px 24px rgba(0,0,0,0.4);
        --shadow-blue: 0 0 20px rgba(59,130,246,0.15);
    }

    /* ── Reset & Background ── */
    html, body {
        background-color: var(--navy-900) !important;
        font-family: 'Inter', sans-serif !important;
        color: var(--text-100) !important;
    }

    /* Grid lines + glow background */
    [data-testid="stAppViewContainer"] {
        background-color: var(--navy-900) !important;
        background-image:
            /* Glow orb kanan atas */
            radial-gradient(ellipse 70% 55% at 75% 5%, rgba(59,130,246,0.18) 0%, transparent 65%),
            /* Glow orb kiri tengah */
            radial-gradient(ellipse 50% 40% at 10% 60%, rgba(99,102,241,0.10) 0%, transparent 60%),
            /* Grid horizontal */
            linear-gradient(rgba(59,130,246,0.055) 1px, transparent 1px),
            /* Grid vertical */
            linear-gradient(90deg, rgba(59,130,246,0.055) 1px, transparent 1px) !important;
        background-size: auto, auto, 52px 52px, 52px 52px !important;
        background-position: 0 0, 0 0, -1px -1px, -1px -1px !important;
        font-family: 'Inter', sans-serif !important;
        color: var(--text-100) !important;
    }

    [data-testid="stMain"], section.main {
        background: transparent !important;
        font-family: 'Inter', sans-serif !important;
        color: var(--text-100) !important;
    }

    [data-testid="stHeader"] {
        background: rgba(6,11,24,0.85) !important;
        backdrop-filter: blur(12px) !important;
        border-bottom: 1px solid var(--border);
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(6,11,24,0.92) !important;
        backdrop-filter: blur(16px) !important;
        border-right: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] * {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── Sidebar nav buttons ── */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 10px !important;
        color: var(--text-400) !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 10px 16px !important;
        margin: 1px 0 !important;
        width: 100% !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
        letter-spacing: 0 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(14,22,40,0.85) !important;
        color: var(--text-200) !important;
        border-color: rgba(59,130,246,0.2) !important;
        box-shadow: none !important;
        transform: none !important;
    }
    /* Active nav button — class ditambah via JS di session state */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: rgba(20,32,58,0.95) !important;
        color: var(--text-100) !important;
        border-color: rgba(59,130,246,0.35) !important;
        border-left: 2px solid var(--blue-500) !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: rgba(20,32,58,0.95) !important;
        transform: none !important;
    }

    /* ── Main content padding ── */
    .block-container {
        padding: 2rem 2.5rem !important;
        max-width: 1100px;
    }

    /* ── Typography ── */
    h1 { font-size: 2rem !important; font-weight: 800 !important; color: var(--text-100) !important; letter-spacing: -0.03em; }
    h2 { font-size: 1.4rem !important; font-weight: 700 !important; color: var(--text-100) !important; }
    h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: var(--text-200) !important; }
    p, li, span { color: var(--text-200) !important; }

    /* ── Cards ── */
    .ftbl-card {
        background: rgba(15,23,41,0.75);
        backdrop-filter: blur(8px);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow);
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .ftbl-card:hover {
        border-color: var(--border-hover);
        box-shadow: var(--shadow-blue);
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: var(--navy-600) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-100) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 0.9rem !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--blue-500) !important;
        box-shadow: 0 0 0 3px var(--blue-glow) !important;
        outline: none !important;
    }
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--text-600) !important;
    }
    /* Label input */
    .stTextInput label, .stTextArea label {
        color: var(--text-400) !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
        color: #fff !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        padding: 0.6rem 1.75rem !important;
        transition: all 0.2s !important;
        box-shadow: 0 2px 12px rgba(59,130,246,0.3) !important;
        letter-spacing: 0.02em !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(59,130,246,0.45) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: var(--navy-700) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
    }
    [data-testid="stExpander"] summary {
        color: var(--text-200) !important;
        font-weight: 500 !important;
    }

    /* ── Status / Alert ── */
    [data-testid="stStatusWidget"],
    .stAlert {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
    }
    .stAlert > div {
        color: var(--text-200) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--navy-600) !important;
        border-radius: var(--radius-sm) !important;
        padding: 4px !important;
        gap: 2px !important;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 6px !important;
        color: var(--text-400) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        padding: 6px 14px !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--blue-500) !important;
        color: #fff !important;
    }

    /* ── Divider ── */
    hr { border-color: var(--border) !important; margin: 1.25rem 0 !important; }

    /* ── Download button ── */
    .stDownloadButton > button {
        background: var(--navy-500) !important;
        border: 1px solid var(--border-hover) !important;
        color: var(--blue-400) !important;
        font-weight: 500 !important;
        border-radius: var(--radius-sm) !important;
    }
    .stDownloadButton > button:hover {
        background: var(--navy-400) !important;
        border-color: var(--blue-500) !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--navy-900); }
    ::-webkit-scrollbar-thumb { background: var(--navy-400); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--navy-300); }

    /* ── Info / Warning boxes ── */
    .stInfo { background: rgba(59,130,246,0.1) !important; border-color: rgba(59,130,246,0.3) !important; }
    .stWarning { background: rgba(245,158,11,0.1) !important; }
    .stError { background: rgba(239,68,68,0.1) !important; }

    /* ══════════════════════════════════════════════════
       MOBILE RESPONSIVE  (max 768px = tablet/HP)
    ══════════════════════════════════════════════════ */
    @media (max-width: 768px) {

        /* Padding utama lebih kecil */
        .block-container {
            padding: 1rem 1rem 2rem !important;
            max-width: 100% !important;
        }

        /* Kolom: wrap jadi 2x2 di tablet */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: calc(50% - 8px) !important;
            flex: 0 0 calc(50% - 8px) !important;
        }

        /* Hero h1 lebih kecil */
        h1 {
            font-size: 1.5rem !important;
            letter-spacing: -0.01em !important;
        }

        /* Sidebar button touch target lebih besar */
        [data-testid="stSidebar"] .stButton > button {
            padding: 13px 16px !important;
            font-size: 0.95rem !important;
        }

        /* Main CTA button */
        .stButton > button {
            min-height: 48px !important;
            font-size: 0.95rem !important;
        }

        /* Input & textarea lebih tinggi untuk touch */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            font-size: 1rem !important;
            padding: 0.75rem 1rem !important;
        }

        /* Cards full-width friendly */
        .ftbl-card {
            padding: 1rem !important;
        }

        /* Expander */
        [data-testid="stExpander"] summary {
            font-size: 0.9rem !important;
        }
    }

    /* ── Handphone portrait (max 480px) ── */
    @media (max-width: 480px) {

        /* Padding lebih agresif */
        .block-container {
            padding: 0.75rem 0.75rem 2rem !important;
        }

        /* Kolom: full-width (stack 1 per baris) */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: 100% !important;
            flex: 0 0 100% !important;
        }

        /* Logo badge di Home — sembunyikan di HP kecil */
        /* (terlalu ramai di layar 360px) */
        h1 {
            font-size: 1.3rem !important;
        }

        /* Tabs font */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.75rem !important;
            padding: 5px 10px !important;
        }

        /* Sembunyikan subtext kecil di sidebar */
        [data-testid="stSidebar"] .stButton > button {
            font-size: 1rem !important;
            min-height: 52px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar() -> str:
    with st.sidebar:
        # Brand header — circuit logo via base64
        logo64 = _logo_img(64)
        st.markdown(f"""
        <div style="padding: 1.5rem 0.75rem 1.25rem; text-align:center;">
            <div style="display:flex; justify-content:center; margin-bottom:12px;">
                {logo64}
            </div>
            <div style="font-size:1.05rem; font-weight:700; color:#f0f4ff;
                        letter-spacing:0.06em; text-transform:uppercase;">FTBL7 LABS</div>
            <div style="font-size:0.65rem; color:#4a5878;
                        letter-spacing:0.12em; text-transform:uppercase;
                        margin-top:3px;">Content Intelligence</div>
        </div>
        <div style="height:1px; background:rgba(59,130,246,0.12); margin: 0 0 1rem;"></div>
        <div style="font-size:0.65rem; color:#4a5878; letter-spacing:0.1em;
                    text-transform:uppercase; padding: 0 0.5rem 0.5rem;
                    font-weight:600;">NAVIGASI</div>
        """, unsafe_allow_html=True)

        # Init session state
        if "page" not in st.session_state:
            st.session_state.page = "Home"

        nav_items = [
            ("⌂", "Home"),
            ("▶", "Clip Detector"),
            ("◈", "Trend & Sentiment"),
            ("⊕", "SEO Optimizer"),
            ("✦", "Content Reviewer"),
        ]

        for icon, name in nav_items:
            is_active = st.session_state.page == name
            btn_type = "primary" if is_active else "secondary"
            if st.button(
                f"{icon}  {name}",
                key=f"nav_{name}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state.page = name
                st.rerun()

        st.markdown("""
        <div style="height:1px; background:rgba(59,130,246,0.12); margin: 1.5rem 0 1rem;"></div>
        <div style="font-size:0.68rem; color:#4a5878; text-align:center; padding-bottom:1rem;">
            v1.0.0 &nbsp;·&nbsp; Powered by Gemini 2.0
        </div>
        """, unsafe_allow_html=True)

        return st.session_state.page


# ── Pages ─────────────────────────────────────────────────────────────────────
def page_home():
    st.markdown("<div style='padding-top:1.25rem'></div>", unsafe_allow_html=True)

    # ── Badge ─────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="display:inline-block;background:rgba(59,130,246,0.12);'
        'border:1px solid rgba(59,130,246,0.25);border-radius:20px;'
        'padding:4px 14px;font-size:0.72rem;font-weight:600;color:#60a5fa;'
        'letter-spacing:0.06em;text-transform:uppercase;margin-bottom:0.75rem;">'
        'Content Intelligence Platform</div>',
        unsafe_allow_html=True,
    )

    # ── Hero text ─────────────────────────────────────────────────────────────
    st.markdown(
        "<h1 style='font-size:clamp(1.4rem,4vw,2.3rem);font-weight:800;"
        "color:#f0f4ff;line-height:1.2;margin:0 0 0.5rem;letter-spacing:-0.02em;'>"
        "Elevate your football content<br>with "
        "<span style='color:#3b82f6;'>AI-powered</span> insights</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:clamp(0.85rem,2.5vw,1rem);color:#7a8fba;"
        "max-width:560px;line-height:1.7;margin-bottom:1.75rem;'>"
        "FTBL7 Labs membantu kreator sepak bola Indonesia mendeteksi momen viral, "
        "riset tren, dan mengoptimasi konten secara otomatis.</p>",
        unsafe_allow_html=True,
    )

    # ── Module cards — 4 kolom desktop, 2x2 tablet, 1 kolom HP (via CSS) ─────
    modules = [
        ("🎬", "Clip Detector",    "Deteksi 5 momen viral otomatis",    "#3b82f6", "AKTIF"),
        ("📊", "Trend & Sentiment","Riset tren sepak bola Indonesia",    "#8b5cf6", "SOON"),
        ("🔍", "SEO Optimizer",    "Optimasi judul & hashtag",           "#10b981", "SOON"),
        ("✍️", "Content Reviewer", "Review naskah sebelum tayang",       "#f59e0b", "SOON"),
    ]
    cols = st.columns(4, gap="small")
    for col, (icon, title, desc, color, status) in zip(cols, modules):
        badge_bg    = "rgba(59,130,246,0.15)" if status == "AKTIF" else "rgba(255,255,255,0.06)"
        badge_color = "#60a5fa"               if status == "AKTIF" else "#4a5878"
        col.markdown(
            f'<div class="ftbl-card" style="border-top:2px solid {color};min-height:140px;">'
            f'<div style="font-size:1.5rem;margin-bottom:8px;">{icon}</div>'
            f'<div style="font-size:0.88rem;font-weight:700;color:#f0f4ff;margin-bottom:4px;">{title}</div>'
            f'<div style="font-size:0.76rem;color:#7a8fba;margin-bottom:12px;line-height:1.5;">{desc}</div>'
            f'<span style="background:{badge_bg};color:{badge_color};padding:2px 9px;'
            f'border-radius:10px;font-size:0.62rem;font-weight:700;'
            f'letter-spacing:0.06em;text-transform:uppercase;">{status}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def page_clip_detector():
    render_clip_detector()


def page_trend_sentiment():
    st.markdown("""
    <div style="padding-top:1rem;">
        <h1>📊 Trend & Sentiment</h1>
        <p style="color:#7a8fba !important;">Riset tren dan analisis sentimen netizen sepak bola Indonesia</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="ftbl-card" style="text-align:center; padding:3.5rem 2rem;">
        <div style="font-size:2.5rem; margin-bottom:1rem;">🚧</div>
        <div style="font-size:1.1rem; font-weight:700; color:#f0f4ff; margin-bottom:0.5rem;">Coming Soon</div>
        <div style="font-size:0.875rem; color:#7a8fba; max-width:420px; margin:0 auto; line-height:1.65;">
            Google Trends integration, Twitter/X sentiment scraping, keyword trending sepak bola Indonesia, dan sentiment scoring per topik.
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_seo_optimizer():
    st.markdown("""
    <div style="padding-top:1rem;">
        <h1>🔍 SEO Optimizer</h1>
        <p style="color:#7a8fba !important;">Optimasi judul, hashtag, dan deskripsi untuk maksimal jangkauan</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="ftbl-card" style="text-align:center; padding:3.5rem 2rem;">
        <div style="font-size:2.5rem; margin-bottom:1rem;">🚧</div>
        <div style="font-size:1.1rem; font-weight:700; color:#f0f4ff; margin-bottom:0.5rem;">Coming Soon</div>
        <div style="font-size:0.875rem; color:#7a8fba; max-width:420px; margin:0 auto; line-height:1.65;">
            Generator judul A/B testing, rekomendasi hashtag real-time, auto-generate deskripsi YouTube, dan CTR score predictor.
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_content_reviewer():
    st.markdown("""
    <div style="padding-top:1rem;">
        <h1>✍️ Content Reviewer</h1>
        <p style="color:#7a8fba !important;">Review naskah dan caption sebelum tayang</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="ftbl-card" style="text-align:center; padding:3.5rem 2rem;">
        <div style="font-size:2.5rem; margin-bottom:1rem;">🚧</div>
        <div style="font-size:1.1rem; font-weight:700; color:#f0f4ff; margin-bottom:0.5rem;">Coming Soon</div>
        <div style="font-size:0.875rem; color:#7a8fba; max-width:420px; margin:0 auto; line-height:1.65;">
            Tone checker, clickbait detector, engagement score prediction, rewrite suggestions, dan script-to-caption converter.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Router ────────────────────────────────────────────────────────────────────
ROUTES = {
    "Home":              page_home,
    "Clip Detector":     page_clip_detector,
    "Trend & Sentiment": page_trend_sentiment,
    "SEO Optimizer":     page_seo_optimizer,
    "Content Reviewer":  page_content_reviewer,
}


def main():
    load_css()
    active = render_sidebar()
    ROUTES.get(active, page_home)()


if __name__ == "__main__":
    main()
