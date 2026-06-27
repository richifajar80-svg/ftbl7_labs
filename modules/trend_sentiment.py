# =============================================================================
# modules/trend_sentiment.py  — [COMING SOON]
# Modul 2: Trend & Sentiment Analysis
# =============================================================================

import streamlit as st


def render():
    st.markdown("""
    <div class="page-header">
        <h1>📊 Trend & Sentiment</h1>
        <p>Riset tren dan analisis sentimen netizen sepak bola Indonesia</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="ftbl7-card" style="text-align:center; padding:3rem;">
        <div style="font-size:3rem; margin-bottom:1rem;">🚧</div>
        <div style="font-size:1.2rem; font-weight:600; color:#e8eaf0; margin-bottom:0.5rem;">Coming Soon</div>
        <div style="font-size:0.875rem; color:#8892a4;">
            Modul ini akan mencakup: Google Trends integration, Twitter/X sentiment scraping,<br>
            keyword trending sepak bola Indonesia, dan sentiment scoring per topik.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    **Fitur yang direncanakan:**
    - 🔥 Real-time trending keywords (Liga Indonesia, Timnas, UCL, dll)
    - 📈 Grafik tren 7/30 hari per topik
    - 😊😡 Sentiment score netizen per pemain/klub
    - 🗓️ Calendar event pertandingan + prediksi viral moment
    """)
