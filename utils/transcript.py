# =============================================================================
# utils/transcript.py
# Multi-layer transcript fetcher — dioptimasi untuk local run
#
# Urutan bypass:
#   1. yt-dlp + cookies dari Chrome (paling ampuh, lokal)
#   2. yt-dlp + cookies dari Edge
#   3. yt-dlp + cookies dari Firefox
#   4. yt-dlp tanpa cookies (fallback)
#   5. youtube-transcript-api (direct API)
# =============================================================================

import re
import os
import tempfile
import subprocess
from typing import Optional


def extract_video_id(url: str) -> Optional[str]:
    """Ekstrak 11-karakter video ID dari URL YouTube."""
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


# ── yt-dlp helpers ────────────────────────────────────────────────────────────

def _run_ytdlp(url: str, extra_args: list = []) -> Optional[str]:
    """
    Jalankan yt-dlp untuk download subtitle .vtt lalu parse ke plain text.
    extra_args: argumen tambahan seperti --cookies-from-browser chrome
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "python", "-m", "yt_dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "id,en",
            "--sub-format", "vtt",
            "--skip-download",
            "--no-playlist",
            "--quiet",
            "-o", os.path.join(tmpdir, "%(id)s"),
        ] + extra_args + [url]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=90,
            )

            for fname in os.listdir(tmpdir):
                if fname.endswith(".vtt"):
                    fpath = os.path.join(tmpdir, fname)
                    with open(fpath, encoding="utf-8") as f:
                        text = _parse_vtt(f.read())
                    if len(text) > 100:
                        return text

        except Exception:
            pass

    return None


def _layer1_ytdlp_chrome(url: str) -> Optional[str]:
    """Layer 1: yt-dlp dengan cookies Chrome (user sudah login YouTube)."""
    return _run_ytdlp(url, ["--cookies-from-browser", "chrome"])


def _layer2_ytdlp_edge(url: str) -> Optional[str]:
    """Layer 2: yt-dlp dengan cookies Edge."""
    return _run_ytdlp(url, ["--cookies-from-browser", "edge"])


def _layer3_ytdlp_firefox(url: str) -> Optional[str]:
    """Layer 3: yt-dlp dengan cookies Firefox."""
    return _run_ytdlp(url, ["--cookies-from-browser", "firefox"])


def _layer4_ytdlp_plain(url: str) -> Optional[str]:
    """Layer 4: yt-dlp tanpa cookies."""
    return _run_ytdlp(url, [])


def _layer5_api(video_id: str) -> Optional[str]:
    """Layer 5: youtube-transcript-api (direct, sering diblokir bot detection)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        tl = YouTubeTranscriptApi.list_transcripts(video_id)

        for manual in [True, False]:
            for lang in ["id", "en", "en-US"]:
                try:
                    t = (tl.find_manually_created_transcript([lang]) if manual
                         else tl.find_generated_transcript([lang]))
                    entries = t.fetch()
                    return " ".join(e.get("text", "") for e in entries).strip()
                except Exception:
                    pass

        # Last resort — transcript pertama yang ada
        for t in tl:
            try:
                return " ".join(e.get("text", "") for e in t.fetch()).strip()
            except Exception:
                pass

    except Exception:
        pass

    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def get_transcript(url: str) -> dict:
    """
    Ambil transkrip dengan 5-layer bypass.

    Returns:
        {
            "success": bool,
            "transcript": str | None,
            "method": str,
            "video_id": str | None,
            "error": str | None,
        }
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {
            "success": False, "transcript": None,
            "method": "none", "video_id": None,
            "error": "URL YouTube tidak valid.",
        }

    layers = [
        ("yt-dlp + Chrome cookies",  lambda: _layer1_ytdlp_chrome(url)),
        ("yt-dlp + Edge cookies",    lambda: _layer2_ytdlp_edge(url)),
        ("yt-dlp + Firefox cookies", lambda: _layer3_ytdlp_firefox(url)),
        ("yt-dlp (no cookies)",      lambda: _layer4_ytdlp_plain(url)),
        ("youtube-transcript-api",   lambda: _layer5_api(video_id)),
    ]

    for method_name, fetch_fn in layers:
        try:
            result = fetch_fn()
            if result and len(result) > 100:
                return {
                    "success": True,
                    "transcript": result,
                    "method": method_name,
                    "video_id": video_id,
                    "error": None,
                }
        except Exception:
            continue

    return {
        "success": False,
        "transcript": None,
        "method": "none",
        "video_id": video_id,
        "error": (
            "Semua metode otomatis gagal. Kemungkinan: "
            "subtitle dinonaktifkan creator, atau video baru (<24 jam). "
            "Gunakan Input Manual."
        ),
    }


# ── VTT parser ────────────────────────────────────────────────────────────────

def _parse_vtt(content: str) -> str:
    """Parse .vtt subtitle → plain text bersih."""
    lines, prev = [], None
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
