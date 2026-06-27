# =============================================================================
# modules/trend_sentiment.py  —  FTBL7 Labs  —  Modul 2
#
# Flow:
#   Input keyword
#     └─► fetch_google_trends()  → pytrends (Indonesia)
#     └─► analyze_with_gemini()  → tren, sentimen, rekomendasi konten
#     └─► render_results()       → chart + cards
# =============================================================================

import json
import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# ─────────────────────────────────────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
.ts-card {
    background: rgba(15,23,41,0.75);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(59,130,246,0.12);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.ts-card:hover {
    border-color: rgba(59,130,246,0.3);
    box-shadow: 0 0 20px rgba(59,130,246,0.08);
}
.ts-label {
    font-size: 0.63rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #4a5878;
    margin-bottom: 6px;
}
.ts-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin: 2px 3px 2px 0;
}
.ts-stat {
    text-align: center;
    padding: 0.75rem 1rem;
}
.ts-stat .num {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
}
.ts-stat .lbl {
    font-size: 0.62rem;
    color: #4a5878;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 4px;
}
.sentiment-bar {
    height: 8px;
    border-radius: 4px;
    margin: 6px 0 2px;
}
.rec-card {
    background: rgba(10,16,32,0.6);
    border: 1px solid rgba(59,130,246,0.1);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.6rem;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE TRENDS FETCHER
# ─────────────────────────────────────────────────────────────────────────────

def fetch_google_trends(keyword: str, timeframe: str = "today 3-m") -> dict:
    """
    Ambil data tren dari Google Trends untuk Indonesia.
    timeframe: 'now 7-d' | 'today 1-m' | 'today 3-m' | 'today 12-m'
    """
    try:
        from pytrends.request import TrendReq

        # Coba cat=20 (Sports) dulu, fallback ke cat=0 jika kosong
        iot = None
        for cat, geo in [(20, "ID"), (0, "ID"), (0, "")]:
            pt = TrendReq(hl="id-ID", tz=420, timeout=(10, 25))
            pt.build_payload([keyword], cat=cat, timeframe=timeframe, geo=geo)
            iot = pt.interest_over_time()
            if not iot.empty and keyword in iot.columns:
                break

        if iot.empty or keyword not in iot.columns:
            return {
                "success": False,
                "error": (
                    f'Keyword "{keyword}" tidak ditemukan di Google Trends Indonesia '
                    f'untuk periode ini. Coba keyword yang lebih populer atau ganti periode ke "1 Bulan" / "3 Bulan".'
                ),
            }

        series = iot[keyword]
        if len(series) == 0:
            return {"success": False, "error": "Data tren kosong — coba periode yang lebih panjang."}

        # Related queries (opsional, tidak gagalkan jika error)
        top_q, rising_q, top_t = [], [], []
        try:
            related  = pt.related_queries()
            top_q    = (related.get(keyword, {}).get("top") or pd.DataFrame()).head(10).to_dict("records")
            rising_q = (related.get(keyword, {}).get("rising") or pd.DataFrame()).head(10).to_dict("records")
        except Exception:
            pass
        try:
            topics = pt.related_topics()
            top_t  = (topics.get(keyword, {}).get("top") or pd.DataFrame()).head(5).to_dict("records")
        except Exception:
            pass

        return {
            "success"       : True,
            "keyword"       : keyword,
            "timeframe"     : timeframe,
            "interest_df"   : iot.reset_index(),
            "top_queries"   : top_q,
            "rising_queries": rising_q,
            "top_topics"    : top_t,
            "current_value" : int(series.iloc[-1]),
            "avg_value"     : int(series.mean()),
            "peak_value"    : int(series.max()),
            "error"         : None,
        }

    except Exception as e:
        return {"success": False, "error": f"Google Trends error: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
#  GEMINI ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_trend_with_gemini(trends_data: dict, api_key: str) -> dict:
    """Kirim data tren ke Gemini → analisis + rekomendasi konten."""
    try:
        from google import genai
    except ImportError:
        return {"success": False, "error": "Library google-genai belum terinstall."}

    client = genai.Client(api_key=api_key)

    keyword     = trends_data.get("keyword", "")
    current_val = trends_data.get("current_value", 0)
    avg_val     = trends_data.get("avg_value", 0)
    peak_val    = trends_data.get("peak_value", 0)
    top_queries = trends_data.get("top_queries", [])
    rising_q    = trends_data.get("rising_queries", [])
    top_topics  = trends_data.get("top_topics", [])

    trend_dir = "NAIK" if current_val > avg_val * 1.1 else \
                "TURUN" if current_val < avg_val * 0.9 else "STABIL"

    prompt = f"""
Kamu adalah analis konten digital sepak bola Indonesia yang sangat berpengalaman.

DATA GOOGLE TRENDS INDONESIA:
- Keyword utama   : {keyword}
- Nilai saat ini  : {current_val}/100
- Rata-rata       : {avg_val}/100
- Puncak tertinggi: {peak_val}/100
- Arah tren       : {trend_dir}
- Top related queries : {[q.get('query','') for q in top_queries[:8]]}
- Rising queries  : {[q.get('query','') for q in rising_q[:8]]}
- Related topics  : {[t.get('topic_title','') for t in top_topics[:5]]}

TUGAS: Berikan analisis mendalam dan rekomendasi konten YouTube untuk kreator sepak bola Indonesia.

OUTPUT: Hanya JSON valid, tidak ada teks lain.

{{
  "ringkasan_tren": "Penjelasan situasi tren saat ini dalam 2-3 kalimat",
  "arah_tren": "NAIK",
  "momentum_score": 7.5,
  "sentimen_publik": {{
    "positif": 45,
    "negatif": 30,
    "netral": 25,
    "dominan": "POSITIF",
    "penjelasan": "Kenapa sentimen seperti ini?"
  }},
  "angle_konten": [
    {{
      "judul": "Angle/topik konten yang direkomendasikan",
      "format": "SHORT",
      "alasan": "Mengapa angle ini relevan dan berpotensi viral",
      "urgency": "TINGGI"
    }}
  ],
  "rekomendasi_judul": [
    "5 judul video YouTube yang paling menarik untuk keyword ini"
  ],
  "hashtag_terbaik": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8"],
  "waktu_posting": {{
    "hari_terbaik": ["Jumat", "Sabtu"],
    "jam_terbaik": "19:00-21:00 WIB",
    "alasan": "Kenapa waktu ini optimal"
  }},
  "peringatan": "Risiko atau hal yang perlu dihindari (kosongkan jika tidak ada)"
}}

Semua analisis harus spesifik untuk pasar Indonesia, bahasa natural dan actionable.
"""

    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"temperature": 0.7, "max_output_tokens": 3000},
            )
            raw = resp.text.strip()
            import re
            m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
            if m:
                raw = m.group(1).strip()
            data = json.loads(raw)
            return {"success": True, "data": data, "error": None}

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Gagal parse JSON dari Gemini: {e}"}
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(35)
                continue
            return {"success": False, "error": f"Gemini error: {e}"}

    return {"success": False, "error": "Rate limit — coba lagi dalam 1 menit."}


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _render_trend_chart(df: pd.DataFrame, keyword: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df[keyword],
        mode="lines",
        line=dict(color="#3b82f6", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.08)",
        hovertemplate="%{x|%d %b %Y}<br>Interest: <b>%{y}</b><extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#7a8fba", size=12),
        xaxis=dict(showgrid=True, gridcolor="rgba(59,130,246,0.06)", zeroline=False, tickformat="%b %Y"),
        yaxis=dict(showgrid=True, gridcolor="rgba(59,130,246,0.06)", zeroline=False, range=[0, 105], title="Interest (0-100)"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=220,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_sentiment_bars(sentimen: dict):
    pos = sentimen.get("positif", 0)
    neg = sentimen.get("negatif", 0)
    net = sentimen.get("netral", 0)
    dominan = sentimen.get("dominan", "NETRAL")
    penjelasan = sentimen.get("penjelasan", "")
    dom_color = {"POSITIF": "#34d399", "NEGATIF": "#f87171", "NETRAL": "#fbbf24"}.get(dominan, "#60a5fa")

    st.markdown(f"""
    <div class="ts-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem;">
            <div class="ts-label">Sentimen Publik</div>
            <span class="ts-badge" style="background:rgba(59,130,246,0.1);color:{dom_color};">Dominan: {dominan}</span>
        </div>
        <div style="margin-bottom:.85rem;font-size:.82rem;color:#7a8fba;">{penjelasan}</div>
        <div style="margin-bottom:.5rem;">
            <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#c8d3ea;"><span>😊 Positif</span><span>{pos}%</span></div>
            <div class="sentiment-bar" style="background:rgba(255,255,255,0.06);"><div style="height:8px;width:{pos}%;background:#34d399;border-radius:4px;"></div></div>
        </div>
        <div style="margin-bottom:.5rem;">
            <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#c8d3ea;"><span>😤 Negatif</span><span>{neg}%</span></div>
            <div class="sentiment-bar" style="background:rgba(255,255,255,0.06);"><div style="height:8px;width:{neg}%;background:#f87171;border-radius:4px;"></div></div>
        </div>
        <div>
            <div style="display:flex;justify-content:space-between;font-size:.78rem;color:#c8d3ea;"><span>😐 Netral</span><span>{net}%</span></div>
            <div class="sentiment-bar" style="background:rgba(255,255,255,0.06);"><div style="height:8px;width:{net}%;background:#fbbf24;border-radius:4px;"></div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_results(trends_data: dict, ai_data: dict):
    keyword   = trends_data.get("keyword", "")
    cur_val   = trends_data.get("current_value", 0)
    avg_val   = trends_data.get("avg_value", 0)
    peak_val  = trends_data.get("peak_value", 0)
    df        = trends_data.get("interest_df")
    top_q     = trends_data.get("top_queries", [])
    rising_q  = trends_data.get("rising_queries", [])

    arah      = ai_data.get("arah_tren", "STABIL")
    momentum  = ai_data.get("momentum_score", 0)
    ringkasan = ai_data.get("ringkasan_tren", "")
    angles    = ai_data.get("angle_konten", [])
    judul_list = ai_data.get("rekomendasi_judul", [])
    hashtags  = ai_data.get("hashtag_terbaik", [])
    sentimen  = ai_data.get("sentimen_publik", {})
    waktu     = ai_data.get("waktu_posting", {})
    peringatan = ai_data.get("peringatan", "")

    arah_color = {"NAIK": "#34d399", "TURUN": "#f87171", "STABIL": "#fbbf24"}.get(arah, "#60a5fa")
    arah_icon  = {"NAIK": "↑", "TURUN": "↓", "STABIL": "→"}.get(arah, "→")

    # ── Stat bar
    st.markdown(f"""
    <div class="ts-card">
        <div style="display:flex;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:180px;">
                <div class="ts-label">Ringkasan Tren</div>
                <div style="font-size:.88rem;color:#e8eaf0;line-height:1.55;">{ringkasan}</div>
            </div>
            <div style="display:flex;gap:0;">
                <div class="ts-stat">
                    <div class="num" style="color:{arah_color};">{arah_icon} {cur_val}</div>
                    <div class="lbl">Sekarang</div>
                </div>
                <div class="ts-stat" style="border-left:1px solid rgba(59,130,246,0.12);">
                    <div class="num" style="color:#60a5fa;">{avg_val}</div>
                    <div class="lbl">Rata-rata</div>
                </div>
                <div class="ts-stat" style="border-left:1px solid rgba(59,130,246,0.12);">
                    <div class="num" style="color:#a78bfa;">{peak_val}</div>
                    <div class="lbl">Puncak</div>
                </div>
                <div class="ts-stat" style="border-left:1px solid rgba(59,130,246,0.12);">
                    <div class="num" style="color:{arah_color};">{momentum}</div>
                    <div class="lbl">Momentum</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Chart + Sentimen
    col_chart, col_sent = st.columns([3, 2])
    with col_chart:
        st.markdown('<div class="ts-card" style="padding-bottom:.5rem;">', unsafe_allow_html=True)
        st.markdown(f'<div class="ts-label">Interest Over Time — "{keyword}" (Indonesia)</div>', unsafe_allow_html=True)
        if df is not None:
            _render_trend_chart(df, keyword)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_sent:
        _render_sentiment_bars(sentimen)

    # ── Related Queries
    col_top, col_rise = st.columns(2)
    with col_top:
        st.markdown('<div class="ts-card">', unsafe_allow_html=True)
        st.markdown('<div class="ts-label">🔍 Top Related Queries</div>', unsafe_allow_html=True)
        for q in top_q[:8]:
            query = q.get("query", "")
            val   = q.get("value", 0)
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;font-size:.8rem;color:#c8d3ea;'
                f'padding:4px 0;border-bottom:1px solid rgba(59,130,246,0.07);">'
                f'<span>{query}</span><span style="color:#60a5fa;font-weight:600;">{val}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_rise:
        st.markdown('<div class="ts-card">', unsafe_allow_html=True)
        st.markdown('<div class="ts-label">🚀 Rising Queries</div>', unsafe_allow_html=True)
        for q in rising_q[:8]:
            query = q.get("query", "")
            val   = q.get("value", "")
            badge = "Breakout" if val == "Breakout" else f"+{val}%"
            color = "#34d399" if val == "Breakout" else "#fbbf24"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;font-size:.8rem;color:#c8d3ea;'
                f'padding:4px 0;border-bottom:1px solid rgba(59,130,246,0.07);">'
                f'<span>{query}</span><span style="color:{color};font-weight:600;">{badge}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Angle Konten
    st.markdown("### 🎯 Rekomendasi Angle Konten")
    for ang in angles:
        urgency   = ang.get("urgency", "SEDANG")
        fmt       = ang.get("format", "SHORT")
        urg_color = {"TINGGI": "#f87171", "SEDANG": "#fbbf24", "RENDAH": "#60a5fa"}.get(urgency, "#60a5fa")
        fmt_color = {"SHORT": "#34d399", "LONG": "#a78bfa", "SERIES": "#60a5fa"}.get(fmt, "#60a5fa")
        st.markdown(f"""
        <div class="ts-card" style="border-left:3px solid {urg_color};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;flex-wrap:wrap;gap:.4rem;">
                <div style="font-size:.9rem;font-weight:600;color:#f0f4ff;">{ang.get('judul','')}</div>
                <div>
                    <span class="ts-badge" style="background:rgba(59,130,246,0.1);color:{fmt_color};">{fmt}</span>
                    <span class="ts-badge" style="background:rgba(239,68,68,0.1);color:{urg_color};">Urgensi: {urgency}</span>
                </div>
            </div>
            <div style="font-size:.8rem;color:#7a8fba;">{ang.get('alasan','')}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Judul + Hashtag + Waktu
    col_j, col_h = st.columns([3, 2])
    with col_j:
        st.markdown('<div class="ts-card">', unsafe_allow_html=True)
        st.markdown('<div class="ts-label">💡 Rekomendasi Judul Video</div>', unsafe_allow_html=True)
        for idx, judul in enumerate(judul_list, 1):
            st.markdown(
                f'<div class="rec-card">'
                f'<span style="color:#3b82f6;font-weight:700;margin-right:8px;">#{idx}</span>'
                f'<span style="font-size:.88rem;color:#e8eaf0;">{judul}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_h:
        tags_html = "".join(
            f'<span class="ts-badge" style="background:rgba(59,130,246,0.12);color:#60a5fa;margin:3px 3px 3px 0;">{t}</span>'
            for t in hashtags
        )
        st.markdown(f"""
        <div class="ts-card">
            <div class="ts-label">🏷️ Hashtag Terbaik</div>
            <div style="margin-top:6px;">{tags_html}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="ts-card">
            <div class="ts-label">📅 Waktu Posting Optimal</div>
            <div style="font-size:.9rem;color:#3b82f6;font-weight:600;margin:4px 0;">{' · '.join(waktu.get('hari_terbaik',[]))}</div>
            <div style="font-size:.82rem;color:#34d399;margin-bottom:6px;">⏰ {waktu.get('jam_terbaik','')}</div>
            <div style="font-size:.78rem;color:#7a8fba;">{waktu.get('alasan','')}</div>
        </div>
        """, unsafe_allow_html=True)

    if peringatan:
        st.warning(f"⚠️ **Perhatian:** {peringatan}")

    # ── JSON Export
    with st.expander("📦 Export JSON"):
        export = {
            "trends"     : {k: v for k, v in trends_data.items() if k != "interest_df"},
            "ai_analysis": ai_data,
        }
        json_str = json.dumps(export, ensure_ascii=False, indent=2)
        st.download_button("⬇️ Download JSON", json_str, "ftbl7_trend_analysis.json", "application/json")


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render():
    """Dipanggil dari app.py saat menu Trend & Sentiment aktif."""
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header
    st.markdown("""
    <div style="padding-top:.5rem;margin-bottom:1.5rem;">
        <h1 style="font-size:1.75rem;font-weight:800;color:#f0f4ff;margin:0 0 4px;">
            📊 Trend & Sentiment
        </h1>
        <p style="color:#7a8fba;font-size:.88rem;margin:0;">
            Riset tren real-time dari Google Trends Indonesia + analisis sentimen via Gemini AI
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Input Form
    st.markdown('<div class="ts-card">', unsafe_allow_html=True)
    st.markdown("#### 🔍 Input Keyword")

    col_kw, col_tf = st.columns([3, 1])
    with col_kw:
        keyword = st.text_input(
            "Keyword",
            placeholder="contoh: Timnas Indonesia, Liga 1, Persija, Marselino",
            help="Nama tim, pemain, kompetisi, atau topik sepak bola Indonesia",
            label_visibility="collapsed",
        )
    with col_tf:
        timeframe_label = st.selectbox(
            "Periode",
            ["7 Hari", "1 Bulan", "3 Bulan", "12 Bulan"],
            index=2,
            label_visibility="collapsed",
        )

    tf_map = {
        "7 Hari"  : "now 7-d",
        "1 Bulan" : "today 1-m",
        "3 Bulan" : "today 3-m",
        "12 Bulan": "today 12-m",
    }
    timeframe = tf_map[timeframe_label]

    # API Key
    _secret_key = ""
    try:
        _secret_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    _key_loaded = bool(_secret_key and _secret_key not in ("", "GANTI_DENGAN_API_KEY_ANDA"))

    if _key_loaded:
        api_key = _secret_key
        st.markdown(
            '<div style="margin-top:8px;display:inline-flex;align-items:center;gap:6px;'
            'background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);'
            'border-radius:8px;padding:6px 12px;font-size:.78rem;color:#34d399;">'
            '🔑 API Key loaded from secrets</div>',
            unsafe_allow_html=True,
        )
    else:
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AQ... atau AIza...",
            help="Dapatkan di aistudio.google.com/app/apikey",
        )

    st.markdown("</div>", unsafe_allow_html=True)

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        run = st.button("📊 Analisis Tren", use_container_width=True, type="primary")

    # ── Eksekusi
    if run:
        if not keyword.strip():
            st.warning("⚠️ Masukkan keyword terlebih dahulu.")
            return
        if not api_key.strip():
            st.warning("⚠️ Masukkan Gemini API Key.")
            return

        # Step 1: Google Trends
        with st.status(f"📡 Mengambil data Google Trends untuk '{keyword}'...", expanded=True) as status:
            st.write("🔄 Koneksi ke Google Trends Indonesia...")
            trends_result = fetch_google_trends(keyword, timeframe)
            if trends_result["success"]:
                status.update(label=f"✅ Data tren berhasil diambil ({timeframe_label})", state="complete")
            else:
                status.update(label=f"❌ {trends_result['error']}", state="error")
                st.error(trends_result["error"])
                st.info("Tips: Coba keyword yang lebih populer atau periode yang lebih pendek.")
                return

        # Step 2: Gemini Analysis
        with st.status("🤖 Menganalisis tren dengan Gemini AI...", expanded=True) as status:
            st.write("Menganalisis sentimen, angle konten, hashtag, waktu posting...")
            ai_result = analyze_trend_with_gemini(trends_result, api_key)
            if ai_result["success"]:
                status.update(label="✅ Analisis AI selesai!", state="complete")
            else:
                status.update(label=f"❌ {ai_result['error']}", state="error")
                st.error(ai_result["error"])
                return

        st.session_state["ts_trends"] = trends_result
        st.session_state["ts_ai"]     = ai_result["data"]
        st.session_state["ts_kw"]     = keyword

        st.markdown(f"### 📈 Hasil Analisis: **{keyword}**")
        _render_results(trends_result, ai_result["data"])

    elif "ts_trends" in st.session_state:
        kw = st.session_state.get("ts_kw", "")
        st.caption(f"📌 Hasil terakhir: **{kw}** — klik Analisis Tren untuk refresh.")
        _render_results(st.session_state["ts_trends"], st.session_state["ts_ai"])
