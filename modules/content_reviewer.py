# =============================================================================
# modules/content_reviewer.py  — [COMING SOON]
# Modul 4: Content Reviewer
# =============================================================================

import streamlit as st


def render():
    st.markdown("""
    <div class="page-header">
        <h1>✍️ Content Reviewer</h1>
        <p>Review naskah dan caption sebelum tayang — deteksi isu & saran perbaikan</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="ftbl7-card" style="text-align:center; padding:3rem;">
        <div style="font-size:3rem; margin-bottom:1rem;">🚧</div>
        <div style="font-size:1.2rem; font-weight:600; color:#e8eaf0; margin-bottom:0.5rem;">Coming Soon</div>
        <div style="font-size:0.875rem; color:#8892a4;">
            Modul ini akan menjadi quality gate sebelum konten dipublish:<br>
            cek tone, fakta, engagement potential, dan potensi kontroversi berlebih.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    **Fitur yang direncanakan:**
    - ✅ Tone checker (terlalu agresif? kurang engaging?)
    - ⚠️ Clickbait detector & moderasi konten
    - 📊 Engagement score prediction
    - 🔄 Rewrite suggestions dengan 3 gaya (formal, santai, viral)
    - 🎙️ Script-to-caption auto converter
    """)
