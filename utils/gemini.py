# =============================================================================
# utils/gemini.py
# Wrapper untuk Google Gemini API.
# Model default: gemini-1.5-pro (terbaik untuk analisis panjang)
# =============================================================================

import json
import re
from typing import Optional
import google.generativeai as genai


def init_gemini(api_key: str):
    """Inisialisasi Gemini dengan API key."""
    genai.configure(api_key=api_key)


def detect_viral_clips(
    transcript: str,
    video_title: str = "",
    model_name: str = "gemini-1.5-pro",
) -> dict:
    """
    Analisis transkrip → deteksi 5 momen paling viral + 3 opsi hook per momen.

    Returns:
        {
            "success": bool,
            "data": { clips: [...], hooks: [...] } | None,
            "raw": str,   # raw response dari Gemini (untuk debugging)
            "error": str | None,
        }
    """

    # ── Prompt Engineering ────────────────────────────────────────────────────
    prompt = f"""
Kamu adalah Senior Content Strategist untuk platform YouTube sepak bola Indonesia dengan spesialisasi viral content detection.

TUGAS:
Analisis transkrip video berikut dan deteksi 5 momen paling berpotensi viral/emosional untuk dijadikan short clip (maksimal 60 detik).

KONTEKS VIDEO:
- Judul: {video_title if video_title else 'Tidak diketahui'}
- Target audiens: Fans sepak bola Indonesia (18-35 tahun)
- Platform target: YouTube Shorts, TikTok, Instagram Reels

TRANSKRIP:
---
{transcript[:8000]}
---

KRITERIA PEMILIHAN MOMEN VIRAL:
1. Kontroversi atau drama (debat, konflik, komentar panas)
2. Momen emosional tinggi (gol dramatis, eliminasi, keberhasilan/kegagalan)
3. Fakta/statistik mengejutkan atau tidak terduga
4. Prediksi atau klaim bold yang provocative
5. Momen humor atau reaksi spontan

INSTRUKSI OUTPUT:
Berikan response dalam format JSON yang valid. HANYA output JSON, tidak ada teks lain.

{{
  "video_summary": "Ringkasan singkat konten video dalam 1-2 kalimat",
  "clips": [
    {{
      "rank": 1,
      "timestamp_hint": "Perkiraan posisi konten (misal: 'awal video', 'pertengahan', '10 menit pertama')",
      "quote": "Kutipan langsung dari transkrip yang mewakili momen ini (max 100 karakter)",
      "topic": "Topik singkat (max 50 karakter)",
      "why_viral": "Alasan spesifik mengapa momen ini berpotensi viral (max 150 karakter)",
      "emotion_trigger": "KONTROVERSI | EMOSIONAL | MENGEJUTKAN | HUMOR | INSPIRATIF",
      "viral_score": 8.5,
      "hooks": {{
        "kontroversial": {{
          "judul": "Hook kontroversial yang memancing debat (max 80 karakter)",
          "caption": "Caption Instagram/TikTok (max 150 karakter) #hashtag",
          "angle": "Sudut pandang yang diambil"
        }},
        "emosional": {{
          "judul": "Hook yang menyentuh perasaan dan empati (max 80 karakter)",
          "caption": "Caption Instagram/TikTok (max 150 karakter) #hashtag",
          "angle": "Sudut pandang yang diambil"
        }},
        "pertanyaan": {{
          "judul": "Hook berupa pertanyaan yang memancing komentar (max 80 karakter)",
          "caption": "Caption Instagram/TikTok (max 150 karakter) #hashtag",
          "angle": "Sudut pandang yang diambil"
        }}
      }}
    }}
  ],
  "top_hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "posting_recommendation": "Rekomendasi waktu dan strategi posting untuk pasar Indonesia"
}}

Pastikan semua teks dalam Bahasa Indonesia yang natural dan engaging untuk audiens sepak bola Indonesia.
"""

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )

        raw_text = response.text.strip()

        # Ekstrak JSON dari response (handle jika ada markdown code block)
        json_text = _extract_json(raw_text)
        data = json.loads(json_text)

        return {
            "success": True,
            "data": data,
            "raw": raw_text,
            "error": None,
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "data": None,
            "raw": raw_text if 'raw_text' in locals() else "",
            "error": f"Gagal parse JSON dari Gemini: {str(e)}. Coba lagi.",
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "raw": "",
            "error": f"Gemini API error: {str(e)}",
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """
    Ekstrak JSON murni dari response Gemini yang mungkin
    membungkusnya dengan markdown ```json ... ```.
    """
    # Coba ekstrak dari code block markdown
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1).strip()

    # Coba temukan objek JSON langsung { ... }
    match = re.search(r"(\{[\s\S]+\})", text)
    if match:
        return match.group(1).strip()

    return text
