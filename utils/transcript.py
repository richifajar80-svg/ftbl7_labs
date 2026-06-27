# =============================================================================
# utils/transcript.py
# Mengambil transkrip YouTube dengan multi-layer bypass strategy.
#
# Strategi (berurutan — jika gagal, lanjut ke berikutnya):
#   1. youtube-transcript-api langsung (paling cepat)
#   2. yt-dlp — mengekstrak subtitle dari .vtt/.srt
#   3. Manual input (dipanggil dari UI, bukan dari sini)
# =============================================================================

import re
import os
import tempfile
import subprocess
from typing import Optional


def extract_video_id(url: str) -> Optional[str]:
    """Ekstrak video ID dari berbagai format URL YouTube."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_via_api(video_id: str, language: str = "id") -> Optional[str]:
    """
    Metode 1: youtube-transcript-api
    Mencoba bahasa Indonesia dulu, fallback ke Inggris, lalu auto-generated.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

        # Prioritas bahasa
        lang_priority = [language, "id", "en", "en-US"]

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Coba manual transcript dulu (lebih akurat)
            for lang in lang_priority:
                try:
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    entries = transcript.fetch()
                    return _entries_to_text(entries)
                except Exception:
                    pass

            # Fallback ke auto-generated
            for lang in lang_priority:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    entries = transcript.fetch()
                    return _entries_to_text(entries)
                except Exception:
                    pass

            # Last resort: ambil yang tersedia apa saja dan translate ke ID
            available = list(transcript_list)
            if available:
                entries = available[0].fetch()
                return _entries_to_text(entries)

        except (TranscriptsDisabled, NoTranscriptFound):
            return None

    except ImportError:
        pass
    except Exception:
        pass

    return None


def fetch_via_ytdlp(url: str) -> Optional[str]:
    """
    Metode 2: yt-dlp
    Download subtitle sebagai .vtt, parse menjadi plain text.
    Berguna saat youtube-transcript-api diblokir oleh IP.
    """
    try:
        import yt_dlp  # noqa: F401 — cek ketersediaan
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(id)s")
        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "id,en",
            "--sub-format", "vtt",
            "--skip-download",
            "--no-playlist",
            "-o", output_template,
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Cari file .vtt yang dihasilkan
            for fname in os.listdir(tmpdir):
                if fname.endswith(".vtt"):
                    vtt_path = os.path.join(tmpdir, fname)
                    with open(vtt_path, "r", encoding="utf-8") as f:
                        return _parse_vtt(f.read())

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

    return None


def get_transcript(url: str) -> dict:
    """
    Fungsi utama: coba semua metode secara berurutan.

    Returns:
        {
            "success": bool,
            "transcript": str | None,
            "method": str,       # "api" | "ytdlp" | "failed"
            "video_id": str | None,
            "error": str | None,
        }
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {
            "success": False,
            "transcript": None,
            "method": "failed",
            "video_id": None,
            "error": "URL YouTube tidak valid. Contoh: https://youtube.com/watch?v=xxxxx",
        }

    # Metode 1: youtube-transcript-api
    transcript = fetch_via_api(video_id)
    if transcript and len(transcript) > 100:
        return {
            "success": True,
            "transcript": transcript,
            "method": "api",
            "video_id": video_id,
            "error": None,
        }

    # Metode 2: yt-dlp
    transcript = fetch_via_ytdlp(url)
    if transcript and len(transcript) > 100:
        return {
            "success": True,
            "transcript": transcript,
            "method": "ytdlp",
            "video_id": video_id,
            "error": None,
        }

    # Semua metode gagal
    return {
        "success": False,
        "transcript": None,
        "method": "failed",
        "video_id": video_id,
        "error": (
            "Transkrip tidak tersedia secara otomatis. "
            "Kemungkinan: subtitle dinonaktifkan, IP diblokir, atau video baru. "
            "Gunakan Input Manual di bawah."
        ),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _entries_to_text(entries: list) -> str:
    """Gabungkan list transcript entries menjadi satu string plain text."""
    return " ".join(entry.get("text", "") for entry in entries if entry.get("text")).strip()


def _parse_vtt(vtt_content: str) -> str:
    """Parse konten VTT menjadi plain text, buang tag HTML dan timestamp."""
    import re
    # Buang header WEBVTT
    lines = vtt_content.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        # Skip baris kosong, header, timestamp, dan cue ID
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", line) or re.match(r"^[\d\s]+$", line):
            continue
        # Buang tag HTML
        clean = re.sub(r"<[^>]+>", "", line)
        clean = re.sub(r"&amp;", "&", clean)
        clean = re.sub(r"&lt;", "<", clean)
        clean = re.sub(r"&gt;", ">", clean)
        clean = clean.strip()
        if clean:
            text_lines.append(clean)

    # Deduplicate baris berurutan yang sama
    deduped = []
    prev = None
    for line in text_lines:
        if line != prev:
            deduped.append(line)
            prev = line

    return " ".join(deduped)
