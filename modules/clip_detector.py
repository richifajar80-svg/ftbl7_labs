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
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
#  CSS TAMBAHAN (diinjeksi sekali saat modul di-load)
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
.cd-card {
    background: #1a1e2a;
    border: 1px solid #252a38;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.cd-card:hover { border-color: rgba(0,212,255,0.3); }

.cd-header {
    border-left: 3px solid #00d4ff;
    padding-left: 0.85rem;
    margin-bottom: 1.25rem;
}
.cd-header h2 { margin: 0; font-size: 1.6rem; color: #e8eaf0; }
.cd-header p  { margin: 0.2rem 0 0; font-size: 0.82rem; color: #8892a4; }

.cd-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #8892a4;
    margin-bottom: 4px;
}
.cd-quote {
    background: #0d0f14;
    border-left: 3px solid #252a38;
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    font-size: 0.82rem;
    color: #8892a4;
    font-style: italic;
    margin: 0.6rem 0;
}
.cd-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.b-red    { background:rgba(255,23,68,0.15);  color:#ff1744; }
.b-cyan   { background:rgba(0,212,255,0.15);  color:#00d4ff; }
.b-purple { background:rgba(124,77,255,0.15); color:#7c4dff; }
.b-orange { background:rgba(255,109,0,0.15);  color:#ff6d00; }
.b-green  { background:rgba(0,230,118,0.15);  color:#00e676; }

.hook-box {
    background: #13161e;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-top: 0.5rem;
}
.hook-title { font-size: 0.95rem; font-weight: 600; color: #e8eaf0; }
.hook-cap   { font-size: 0.8rem;  color: #c8ccd6; margin-top: 4px; }
.hook-angle { font-size: 0.75rem; color: #8892a4; margin-top: 4px; font-style: italic; }

.json-out {
    background: #0d0f14;
    border: 1px solid #252a38;
    border-radius: 8px;
    padding: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #00e676;
    overflow-x: auto;
    white-space: pre-wrap;
    max-height: 400px;
    overflow-y: auto;
}
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


def _layer1_api(video_id: str) -> str | None:
    """Layer 1 — youtube-transcript-api (langsung dari YouTube)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
        tl = YouTubeTranscriptApi.list_transcripts(video_id)

        # Prioritas: manual ID → manual EN → auto ID → auto EN → apapun
        for manual in [True, False]:
            for lang in ["id", "en", "en-US"]:
                try:
                    t = (tl.find_manually_created_transcript([lang]) if manual
                         else tl.find_generated_transcript([lang]))
                    return _entries_to_text(t.fetch())
                except Exception:
                    pass

        # Last resort — ambil transcript pertama yang ada
        for t in tl:
            try:
                return _entries_to_text(t.fetch())
            except Exception:
                pass

    except Exception:
        pass
    return None


def _layer2_ytdlp(url: str) -> str | None:
    """Layer 2 — yt-dlp subtitle download (bypass IP restriction cloud)."""
    try:
        import yt_dlp  # cek tersedia
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "yt-dlp",
            "--write-auto-sub", "--write-sub",
            "--sub-lang", "id,en",
            "--sub-format", "vtt",
            "--skip-download", "--no-playlist",
            "-o", os.path.join(tmpdir, "%(id)s"),
            url,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)
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
    Ambil transkrip dengan 2-layer otomatis.

    Return:
        { success, transcript, method, video_id, error }
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return {"success": False, "transcript": None, "method": "none",
                "video_id": None, "error": "URL YouTube tidak valid."}

    t = _layer1_api(video_id)
    if t and len(t) > 100:
        return {"success": True, "transcript": t, "method": "youtube-transcript-api",
                "video_id": video_id, "error": None}

    t = _layer2_ytdlp(url)
    if t and len(t) > 100:
        return {"success": True, "transcript": t, "method": "yt-dlp",
                "video_id": video_id, "error": None}

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
    Kirim transkrip ke Gemini 1.5 Pro.
    Return: { success, data, raw, error }
    """
    try:
        import google.generativeai as genai
    except ImportError:
        return {"success": False, "data": None, "raw": "",
                "error": "Library google-generativeai belum terinstall. Jalankan: pip install google-generativeai"}

    genai.configure(api_key=api_key)

    prompt = f"""
Kamu adalah Senior Content Strategist untuk platform YouTube sepak bola Indonesia.

TUGAS: Analisis transkrip di bawah ini, lalu deteksi 5 momen paling berpotensi viral/emosional untuk dijadikan short clip (≤60 detik).

KONTEKS:
- Judul video : {title or 'tidak diketahui'}
- Target      : Fans sepak bola Indonesia usia 18–35 tahun
- Platform    : YouTube Shorts, TikTok, Instagram Reels

TRANSKRIP (maks 8000 karakter):
---
{transcript[:8000]}
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

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        resp  = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )
        raw   = resp.text.strip()
        data  = json.loads(_extract_json(raw))
        return {"success": True, "data": data, "raw": raw, "error": None}

    except json.JSONDecodeError as e:
        return {"success": False, "data": None,
                "raw": locals().get("raw", ""),
                "error": f"Gagal parse JSON dari Gemini: {e}"}
    except Exception as e:
        return {"success": False, "data": None, "raw": "",
                "error": f"Gemini API error: {e}"}


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
        <p>Deteksi otomatis 5 momen viral dari video YouTube — powered by Gemini 1.5 Pro</p>
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

        api_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Dapatkan gratis di aistudio.google.com/app/apikey",
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
            st.warning("⚠️ Masukkan Gemini API Key.")
            return

        # ── Step 1: Fetch Transkrip ───────────────────────────────────────
        with st.status("📥 Mengambil transkrip...", expanded=True) as status:
            st.write("Layer 1 — youtube-transcript-api...")
            result = fetch_transcript(url)

            if result["success"]:
                status.update(
                    label=f"✅ Transkrip ditemukan via {result['method']} ({len(result['transcript'])} karakter)",
                    state="complete",
                )
            else:
                st.write(f"❌ {result['error']}")
                status.update(label="⚠️ Transkrip otomatis gagal", state="error")
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
