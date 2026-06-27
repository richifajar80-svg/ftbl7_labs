# FTBL7 Labs Dashboard

One-Stop Content Intelligence Platform untuk YouTube Sepak Bola Indonesia.

## Cara Menjalankan

```bash
cd ftbl7_dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Struktur File

```
ftbl7_dashboard/
├── app.py                    # Entry point, sidebar nav, CSS
├── requirements.txt
├── modules/
│   ├── clip_detector.py      # Modul 1 — AKTIF ✅
│   ├── trend_sentiment.py    # Modul 2 — Coming Soon
│   ├── seo_optimizer.py      # Modul 3 — Coming Soon
│   └── content_reviewer.py   # Modul 4 — Coming Soon
└── utils/
    ├── transcript.py         # YouTube transcript fetcher (multi-method)
    └── gemini.py             # Gemini API wrapper
```

## API Keys

- **Gemini API Key**: https://aistudio.google.com/app/apikey
