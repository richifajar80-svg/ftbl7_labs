# =============================================================================
# modules/clip_detector.py  —  FTBL7 Labs  —  Modul 1
#
# Flow lengkap:
#   Input URL + API Key
#     └─► fetch_transcript()  → 3-layer bypass
#           ├─ Layer 1: youtube-transcript-api
#           ├─ Layer 2: yt-dlp
#           └─ Layer 3: manual input (fallback UI)
#     └─► analyze_with_gemini()
#           └─► render_results()
# =============================================================================

import re
import os
import json
import tempfile
import subprocess
from typing import Optional
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
#  CSS TAMBAHAN (diinjeksi sekali saat modul di-load)
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── Clip Detector component styles (matches app.py navy theme) ── */

.cd-card {
    background: rgba(15,23,41,0.75);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(59,130,246,0.12);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.cd-card:hover {
    border-color: rgba(59,130,246,0.32);
    box-shadow: 0 0 24px rgba(59,130,246,0.1);
}

.cd-header { margin-bottom: 1.5rem; }
.cd-header h2 {
    margin: 0 0 4px;
    font-size: 1.75rem !important;
    font-weight: 800 !important;
    color: #f0f4ff !important;
    letter-spacing: -0.02em;
}
.cd-header p { margin: 0; font-size: 0.875rem; color: #7a8fba !important; }

.cd-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #4a5878;
    margin-bottom: 5px;
}

.cd-quote {
    background: rgba(0,0,0,0.3);
    border-left: 3px solid rgba(59,130,246,0.4);
    padding: 0.5rem 0.85rem;
    border-radius: 0 6px 6px 0;
    font-size: 0.83rem;
    color: #7a8fba !important;
    font-style: italic;
    margin: 0.65rem 0;
    line-height: 1.5;
}

.cd-badge {
    display: inline-block;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.b-red    { background:rgba(239,68,68,0.15);   color:#f87171; }
.b-cyan   { background:rgba(59,130,246,0.15);   color:#60a5fa; }
.b-purple { background:rgba(139,92,246,0.15);   color:#a78bfa; }
.b-orange { background:rgba(245,158,11,0.15);   color:#fbbf24; }
.b-green  { background:rgba(16,185,129,0.15);   color:#34d399; }

.hook-box {
    background: #0b1120;
    border: 1px solid rgba(59,130,246,0.1);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-top: 0.5rem;
}
.hook-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f0f4ff !important;
    line-height: 1.4;
}
.hook-cap {
    font-size: 0.82rem;
    color: #c8d3ea !important;
    margin-top: 5px;
    line-height: 1.5;
}
.hook-angle {
    font-size: 0.75rem;
    color: #4a5878 !important;
    margin-top: 5px;
    font-style: italic;
}

.json-out {
    background: #060b18;
    border: 1px solid rgba(59,130,246,0.15);
    border-radius: 10px;
    padding: 1rem;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.76rem;
    color: #34d399;
    overflow-x: auto;
    white-space: pre-wrap;
    max-height: 420px;
    overflow-y: auto;
    line-height: 1.6;
}

.summary-stat {
    text-align: center;
    padding: 0.5rem 1.5rem;
    border-left: 1px solid rgba(59,130,246,0.15);
}
.summary-stat .num { font-size: 2.2rem; font-weight: 800; color: #3b82f6; line-height: 1; }
.summary-stat .lbl { font-size: 0.65rem; color: #4a5878; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  TRANSCRIPT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_video_id(url: str) -> str | None:
    """Ekstrak 11-karakter video ID dari berbagai format URL YouTube."""
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def _entries_to_text(entries: list) -> str:
    """Gabungkan list transcript entries → plain text."""
    return " ".join(e.get("text", "") for e in entries if e.get("text")).strip()


def _parse_vtt(content: str) -> str:
    """Parse .vtt subtitle file → plain text tanpa tag & timestamp."""
    lines, seen, prev = [], set(), None
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", line) or re.match(r"^[\d\s]+$", line):
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        if clean and clean != prev:
            lines.append(clean)
            prev = clean
    return " ".join(lines)


def _run_ytdlp(url: str, extra_args: list = []) -> Optional[str]:
    """Jalankan yt-dlp dengan argumen tambahan, return plain text atau None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "python", "-m", "yt_dlp",
            "--write-auto-sub", "--write-sub",
            "--sub-lang", "id,en",
            "--sub-format", "vtt",
            "--skip-download", "--no-playlist",
            "--quiet",
            "-o", os.path.join(tmpdir, "%(id)s"),
        ] + extra_args + [url]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            for fname in os.listdir(tmpdir):
                if fname.endswith(".vtt"):
                    with open(os.path.join(tmpdir, fname), encoding="utf-8") as f:
                        text = _parse_vtt(f.read())
                    if len(text) > 100:
                        return text
        except Exception:
            pass
    return None


def fetch_transcript(url: str) -> dict:
    """
    Ambil transkrip dengan 5-layer bypass otomatis.
    Urutan: Chrome cookies → Edge cookies → Firefox cookies → no cookies → transcript-api

    Return:
        { success, transcript, method, video_id, error }
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return {"success": False, "transcript": None, "method": "none",
                "video_id": None, "error": "URL YouTube tidak valid."}

    # ── Deteksi environment: cloud tidak punya browser ───────────────────────
    import os
    is_cloud = os.environ.get("STREAMLIT_SHARING_MODE") or \
               os.environ.get("HOME", "").startswith("/home/appuser") or \
               not os.path.exists(os.path.expanduser("~/.config/google-chrome"))

    # ── Layer 1–4: yt-dlp (skip browser cookies di cloud) ────────────────────
    if is_cloud:
        layers = [("yt-dlp", [])]
    else:
        layers = [
            ("yt-dlp + Chrome", ["--cookies-from-browser", "chrome"]),
            ("yt-dlp + Edge",   ["--cookies-from-browser", "edge"]),
            ("yt-dlp + Firefox",["--cookies-from-browser", "firefox"]),
            ("yt-dlp",          []),
        ]
    for method_name, args in layers:
        t = _run_ytdlp(url, args)
        if t and len(t) > 100:
            return {"success": True, "transcript": t, "method": method_name,
                    "video_id": video_id, "error": None}

    # ── Layer 5: youtube-transcript-api ──────────────────────────────────────
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        tl = YouTubeTranscriptApi.list_transcripts(video_id)
        for manual in [True, False]:
            for lang in ["id", "en", "en-US"]:
                try:
                    t = (tl.find_manually_created_transcript([lang]) if manual
                         else tl.find_generated_transcript([lang]))
                    text = _entries_to_text(t.fetch())
                    if len(text) > 100:
                        return {"success": True, "transcript": text,
                                "method": "youtube-transcript-api",
                                "video_id": video_id, "error": None}
                except Exception:
                    pass
        for t in tl:
            try:
                text = _entries_to_text(t.fetch())
                if len(text) > 100:
                    return {"success": True, "transcript": text,
                            "method": "youtube-transcript-api",
                            "video_id": video_id, "error": None}
            except Exception:
                pass
    except Exception:
        pass

    return {
        "success": False, "transcript": None, "method": "none",
        "video_id": video_id,
        "error": "Transkrip tidak tersedia (subtitle off / IP diblokir). Gunakan Input Manual.",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GEMINI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """Keluarkan JSON murni dari response Gemini (bisa terbungkus markdown)."""
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\{[\s\S]+\})", text)
    if m:
        return m.group(1).strip()
    return text


def analyze_with_gemini(transcript: str, title: str, api_key: str) -> dict:
    """
    Kirim transkrip ke Gemini 2.0 Flash via SDK baru (google-genai).
    Support key format AQ. (AI Studio terbaru) maupun AIza (lama).
    Return: { success, data, raw, error }
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        return {"success": False, "data": None, "raw": "",
                "error": "Library google-genai belum terinstall. Jalankan: pip install google-genai"}

    client = genai.Client(api_key=api_key)

    prompt = f"""
Kamu adalah Senior Content Strategist untuk platform YouTube sepak bola Indonesia.

TUGAS: Analisis transkrip di bawah ini, lalu deteksi 5 momen paling berpotensi viral/emosional untuk dijadikan short clip (≤60 detik).

KONTEKS:
- Judul video : {title or 'tidak diketahui'}
- Target      : Fans sepak bola Indonesia usia 18–35 tahun
- Platform    : YouTube Shorts, TikTok, Instagram Reels

TRANSKRIP (maks 5000 karakter):
---
{transcript[:5000]}
---

KRITERIA MOMEN VIRAL:
1. Kontroversi / drama / komentar panas
2. Momen emosional tinggi (gol, eliminasi, kejatuhan)
3. Fakta / statistik mengejutkan
4. Prediksi atau klaim bold
5. Humor / reaksi spontan

OUTPUT: Hanya JSON valid, tidak ada teks lain.

{{
  "video_summary": "Ringkasan 1–2 kalimat",
  "clips": [
    {{
      "rank": 1,
      "timestamp_hint": "Perkiraan posisi (misal: 'awal video', '5 menit pertama')",
      "quote": "Kutipan langsung dari transkrip, maks 120 karakter",
      "topic": "Topik singkat, maks 60 karakter",
      "why_viral": "Alasan spesifik, maks 150 karakter",
      "emotion_trigger": "KONTROVERSI | EMOSIONAL | MENGEJUTKAN | HUMOR | INSPIRATIF",
      "viral_score": 8.5,
      "hooks": {{
        "kontroversial": {{
          "judul": "Hook yang memancing debat, maks 80 karakter",
          "caption": "Caption media sosial + hashtag, maks 160 karakter",
          "angle": "Sudut pandang, maks 60 karakter"
        }},
        "emosional": {{
          "judul": "Hook yang menyentuh perasaan, maks 80 karakter",
          "caption": "Caption media sosial + hashtag, maks 160 karakter",
          "angle": "Sudut pandang, maks 60 karakter"
        }},
        "pertanyaan": {{
          "judul": "Hook berupa pertanyaan, maks 80 karakter",
          "caption": "Caption media sosial + hashtag, maks 160 karakter",
          "angle": "Sudut pandang, maks 60 karakter"
        }}
      }}
    }}
  ],
  "top_hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "posting_recommendation": "Strategi & waktu terbaik posting untuk Indonesia"
}}

Semua teks harus Bahasa Indonesia yang natural dan engaging.
"""

    import time

    # Auto-retry 2x jika kena rate limit (429)
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 4096,
                },
            )
            raw  = resp.text.strip()
            data = json.loads(_extract_json(raw))
            return {"success": True, "data": data, "raw": raw, "error": None}

        except json.JSONDecodeError as e:
            return {"success": False, "data": None,
                    "raw": locals().get("raw", ""),
                    "error": f"Gagal parse JSON dari Gemini: {e}"}

        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < 2:
                time.sleep(35)
                continue
            return {"success": False, "data": None, "raw": "",
                    "error": f"Gemini API error: {e}"}

    return {"success": False, "data": None, "raw": "",
            "error": "Gemini rate limit: semua retry gagal. Tunggu 1 menit lalu coba lagi."}


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_EMOTION_BADGE = {
    "KONTROVERSI": "b-red",
    "EMOSIONAL":   "b-cyan",
    "MENGEJUTKAN": "b-orange",
    "HUMOR":       "b-green",
    "INSPIRATIF":  "b-purple",
}

_SCORE_COLOR = lambda s: "#00e676" if s >= 8 else "#ff6d00" if s >= 6 else "#ff1744"

_HOOK_TABS = [
    ("🔥 Kontroversial", "kontroversial"),
    ("💙 Emosional",     "emosional"),
    ("❓ Pertanyaan",    "pertanyaan"),
]


def _render_clip_card(clip: dict):
    """Render satu kartu momen viral + 3 tab hook."""
    rank    = clip.get("rank", "?")
    topic   = clip.get("topic", "")
    quote   = clip.get("quote", "")
    why     = clip.get("why_viral", "")
    emotion = clip.get("emotion_trigger", "")
    score   = float(clip.get("viral_score", 0))
    ts      = clip.get("timestamp_hint", "")
    hooks   = clip.get("hooks", {})
    color   = _SCORE_COLOR(score)
    ebadge  = _EMOTION_BADGE.get(emotion, "b-cyan")

    st.markdown(f"""
    <div class="cd-card" style="border-left: 3px solid {color};">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:.5rem;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="font-size:1.4rem;font-weight:700;color:{color};min-width:26px;">#{rank}</div>
                <div>
                    <div style="font-size:.95rem;font-weight:600;color:#e8eaf0;">{topic}</div>
                    <div style="font-size:.72rem;color:#8892a4;">⏱️ {ts}</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span class="cd-badge {ebadge}">{emotion}</span>
                <div style="text-align:right;">
                    <div style="font-size:1.2rem;font-weight:700;color:{color};">{score}</div>
                    <div style="font-size:.6rem;color:#8892a4;">VIRAL SCORE</div>
                </div>
            </div>
        </div>
        <div class="cd-quote">"{quote}"</div>
        <div style="font-size:.8rem;color:#8892a4;margin-bottom:.75rem;">💡 {why}</div>
        <div style="height:4px;background:#252a38;border-radius:2px;">
            <div style="height:4px;width:{min(int(score*10),100)}%;background:{color};border-radius:2px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 3 Hook Tabs ──────────────────────────────────────────────────────────
    tabs = st.tabs([label for label, _ in _HOOK_TABS])
    for tab, (_, key) in zip(tabs, _HOOK_TABS):
        h = hooks.get(key, {})
        if not h:
            continue
        with tab:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                <div class="hook-box">
                    <div class="cd-label">JUDUL / HOOK</div>
                    <div class="hook-title">{h.get('judul','')}</div>
                    <div class="cd-label" style="margin-top:.6rem;">CAPTION</div>
                    <div class="hook-cap">{h.get('caption','')}</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="hook-box" style="height:100%;">
                    <div class="cd-label">ANGLE</div>
                    <div class="hook-angle">{h.get('angle','')}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)


def _render_results(data: dict):
    """Render seluruh hasil analisis Gemini."""
    clips    = data.get("clips", [])
    hashtags = data.get("top_hashtags", [])
    posting  = data.get("posting_recommendation", "")
    summary  = data.get("video_summary", "-")

    # ── Summary bar ──────────────────────────────────────────────────────────
    badges = "".join(
        f'<span class="cd-badge b-cyan" style="margin-right:4px;">{t}</span>'
        for t in hashtags
    )
    st.markdown(f"""
    <div class="cd-card">
        <div style="display:flex;align-items:flex-start;gap:1.5rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:220px;">
                <div class="cd-label">RINGKASAN VIDEO</div>
                <div style="font-size:.9rem;color:#e8eaf0;">{summary}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:2rem;font-weight:700;color:#00d4ff;">{len(clips)}</div>
                <div class="cd-label">MOMEN</div>
            </div>
        </div>
        <div style="margin-top:.85rem;">
            <div class="cd-label">TOP HASHTAGS</div>
            <div style="margin-top:4px;">{badges}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if posting:
        st.info(f"📅 **Rekomendasi posting:** {posting}")

    st.markdown("### 🎯 5 Momen Viral Terdeteksi")
    for clip in clips:
        _render_clip_card(clip)

    # ── JSON Export ───────────────────────────────────────────────────────────
    with st.expander("📦 Export JSON"):
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.markdown(f'<div class="json-out">{json_str}</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Download JSON", json_str,
                           "ftbl7_clip_analysis.json", "application/json")


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render():
    """Dipanggil dari app.py saat menu Clip Detector aktif."""

    # Inject CSS modul ini
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="cd-header">
        <h2>🎬 Clip Detector</h2>
        <p>Deteksi otomatis 5 momen viral dari video YouTube — powered by Gemini 2.0 Flash</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Form Input ───────────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="cd-card">', unsafe_allow_html=True)
        st.markdown("#### ⚙️ Input")

        col_url, col_title = st.columns([3, 1])
        with col_url:
            url = st.text_input(
                "URL YouTube",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Format: youtube.com/watch?v=, youtu.be/, /shorts/",
            )
        with col_title:
            title = st.text_input(
                "Judul Video (opsional)",
                placeholder="Misal: Derby Indonesia 2024",
            )

        # ── API Key: baca dari st.secrets dulu, fallback ke manual input ────
        _secret_key = ""
        try:
            _secret_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass
        _key_loaded = bool(_secret_key and _secret_key not in ("", "GANTI_DENGAN_API_KEY_ANDA"))

        if _key_loaded:
            api_key = _secret_key
            st.markdown(
                '<div style="display:flex;align-items:center;gap:8px;'
                'background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);'
                'border-radius:8px;padding:8px 14px;font-size:0.8rem;color:#34d399;">'
                '🔑 API Key loaded from secrets — siap digunakan</div>',
                unsafe_allow_html=True,
            )
        else:
            api_key = st.text_input(
                "🔑 Gemini API Key",
                type="password",
                placeholder="AQ... atau AIza...",
                help="Isi secrets.toml agar tidak perlu input setiap kali. "
                     "Dapatkan key di aistudio.google.com/app/apikey",
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Tombol Analisis ───────────────────────────────────────────────────────
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        run = st.button("🚀 Analisis Sekarang", use_container_width=True)

    if run:
        # Validasi
        if not url.strip():
            st.warning("⚠️ Masukkan URL YouTube.")
            return
        if not api_key.strip():
            st.warning("⚠️ Isi Gemini API Key di .streamlit/secrets.toml atau input di atas.")
            return

        # ── Step 1: Fetch Transkrip ───────────────────────────────────────
        import os as _os
        _on_cloud = (
            _os.environ.get("STREAMLIT_SHARING_MODE")
            or _os.environ.get("HOME", "").startswith("/home/appuser")
        )
        with st.status("📥 Mengambil transkrip otomatis...", expanded=True) as status:
            if _on_cloud:
                st.write("☁️ Mode cloud — mencoba yt-dlp & youtube-transcript-api...")
            else:
                st.write("🔄 Mencoba Layer 1 — yt-dlp + Chrome cookies...")
                st.write("🔄 Mencoba Layer 2 — yt-dlp + Edge cookies...")
                st.write("🔄 Mencoba Layer 3 — yt-dlp + Firefox cookies...")
                st.write("🔄 Mencoba Layer 4 — yt-dlp tanpa cookies...")
            st.write("🔄 Mencoba youtube-transcript-api...")
            result = fetch_transcript(url)

            if result["success"]:
                status.update(
                    label=f"✅ Transkrip via {result['method']} ({len(result['transcript'])} karakter)",
                    state="complete",
                )
            else:
                st.write(f"❌ {result['error']}")
                status.update(label="⚠️ Transkrip otomatis gagal", state="error")
                if _on_cloud:
                    st.warning(
                        "Di Streamlit Cloud, subtitle harus aktif di video. "
                        "Gunakan **Input Manual** di bawah untuk copy-paste transkrip."
                    )
                else:
                    st.info("Gunakan **Input Manual Transkrip** di bawah untuk melanjutkan.")

        if result["success"]:
            transcript = result["transcript"]
            st.session_state["cd_transcript"] = transcript

            with st.expander("📄 Preview Transkrip"):
                st.text(transcript[:600] + ("..." if len(transcript) > 600 else ""))

            # ── Step 2: Gemini Analysis ───────────────────────────────────
            with st.status("🤖 Menganalisis dengan Gemini 1.5 Pro...", expanded=True) as status:
                st.write("Mendeteksi momen viral & membuat hook options...")
                gresult = analyze_with_gemini(transcript, title, api_key)

                if gresult["success"]:
                    status.update(label="✅ Analisis selesai!", state="complete")
                else:
                    status.update(label=f"❌ {gresult['error']}", state="error")
                    st.error(gresult["error"])
                    return

            st.session_state["cd_result"] = gresult["data"]
            _render_results(gresult["data"])

    # ── Tampilkan hasil sebelumnya (jika ada di session) ─────────────────────
    elif "cd_result" in st.session_state and not run:
        st.caption("📌 Menampilkan hasil analisis terakhir. Klik Analisis Sekarang untuk refresh.")
        _render_results(st.session_state["cd_result"])

    # ── Manual Input (selalu tampil di bawah sebagai fallback) ───────────────
    st.markdown("---")
    with st.expander("✍️ Input Manual Transkrip (Fallback)"):
        st.markdown("""
        <div style="font-size:.82rem;color:#8892a4;margin-bottom:.75rem;">
        Cara dapat transkrip manual:<br>
        1. Buka video YouTube → klik <b>⋮</b> → <b>Open transcript</b> → copy semua<br>
        2. Atau pakai ekstensi Chrome: <a href="https://tactiq.io" target="_blank" style="color:#00d4ff;">Tactiq.io</a>
        </div>
        """, unsafe_allow_html=True)

        manual_text = st.text_area(
            "Paste transkrip:",
            height=200,
            placeholder="Paste teks transkrip di sini...",
            key="cd_manual_text",
        )
        manual_title = st.text_input(
            "Judul video:",
            key="cd_manual_title",
        )
        manual_key = st.text_input(
            "Gemini API Key:",
            type="password",
            key="cd_manual_key",
            help="Bisa berbeda dari input di atas",
        )

        if st.button("🤖 Analisis Manual", key="cd_btn_manual"):
            if not manual_text.strip():
                st.warning("⚠️ Paste transkrip terlebih dahulu.")
            elif not manual_key.strip():
                st.warning("⚠️ Masukkan Gemini API Key.")
            else:
                with st.status("🤖 Menganalisis transkrip manual...", expanded=True) as status:
                    st.write("Mengirim ke Gemini 1.5 Pro...")
                    gresult = analyze_with_gemini(manual_text, manual_title, manual_key)

                    if gresult["success"]:
                        status.update(label="✅ Selesai!", state="complete")
                        st.session_state["cd_result"] = gresult["data"]
                        _render_results(gresult["data"])
                    else:
                        status.update(label=f"❌ {gresult['error']}", state="error")
                        st.error(gresult["error"])
