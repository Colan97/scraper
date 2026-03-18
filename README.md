# 🔍 ChatGPT Citation Tracker – Delhi, India

A Streamlit app that queries the **DataForSEO ChatGPT LLM Scraper API** to track which URLs/sources ChatGPT cites when answering your prompts — targeted to **Delhi, India**.

## 📊 What It Does

| Input | Output |
|-------|--------|
| Your prompts / keywords | Table: Prompt → URL → Position (1st, 2nd, 3rd cited) |
| Delhi, India location | Domain, Title, Snippet for each source |
| DataForSEO credentials | Downloadable CSV export |

## 🚀 Deploy in 3 Steps

### 1. Fork / Clone this repo on GitHub

### 2. Deploy to Streamlit Cloud
- Go to [share.streamlit.io](https://share.streamlit.io)
- Connect your GitHub repo
- Set `app.py` as the main file
- Add secrets (see below)

### 3. Add API Credentials in Streamlit Cloud
Go to **App Settings → Secrets** and paste:
```toml
# .streamlit/secrets.toml  (DO NOT commit this file to GitHub)
DATAFORSEO_LOGIN    = "your@email.com"
DATAFORSEO_PASSWORD = "your_api_password"
```
You can also enter credentials directly in the app sidebar at runtime.

## 🔑 DataForSEO API Used

**Endpoint:** `POST /v3/ai_optimization/chat_gpt/llm_scraper/live/advanced`

**Key parameters used:**
```json
{
  "keyword":          "best CA firm in Delhi",
  "location_name":    "Delhi,India",
  "language_name":    "English",
  "force_web_search": true
}
```

**Response parsed:** `sources[]` array → each source has `url`, `domain`, `title`, `snippet`

## 💰 Pricing
Each API call costs ~$0.004 on DataForSEO pay-as-you-go. No monthly subscription needed.

## 📁 Files
```
├── app.py              # Main Streamlit app
├── requirements.txt    # Python dependencies
└── README.md
```
