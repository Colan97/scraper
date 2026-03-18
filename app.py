import streamlit as st
import requests
import base64
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ChatGPT Source Rank Tracker – Delhi",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 ChatGPT Source Rank Tracker")
st.markdown("**📍 Delhi, India** — Enter your prompts, see which URLs ChatGPT cites & their rank position.")
st.markdown("---")

# ── Sidebar – credentials ─────────────────────
with st.sidebar:
    st.header("⚙️ API Credentials")
    st.markdown("Get from [DataForSEO Dashboard](https://app.dataforseo.com/api-access)")
    api_login    = st.text_input("Login (email)", placeholder="you@example.com")
    api_password = st.text_input("Password", type="password")
    st.markdown("---")
    st.markdown("**📍 Location:** Delhi, India (fixed)")
    st.markdown("**🤖 Engine:** ChatGPT + Web Search")
    st.markdown("**💰 Cost:** ~$0.004 per prompt")

# ── Main – prompts only ───────────────────────
st.subheader("📝 Enter Your Prompts")
st.caption("One prompt per line. The app queries ChatGPT for each and extracts all cited sources + their rank.")

prompts_input = st.text_area(
    label="Prompts",
    height=180,
    placeholder="best CA firm in Delhi\ntop digital marketing agency in Delhi NCR\nbest real estate developer South Delhi",
    label_visibility="collapsed",
)

run_btn = st.button("🚀 Run – Find Cited Sources", type="primary", use_container_width=True)

# ── API call ──────────────────────────────────
ENDPOINT = "https://api.dataforseo.com/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced"

def call_api(keyword: str, login: str, password: str) -> dict:
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json",
    }
    payload = [{
        "keyword":          keyword,
        "location_name":    "Delhi,India",
        "language_name":    "English",
        "force_web_search": True,
    }]
    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=130)
    r.raise_for_status()
    return r.json()

def parse_sources(raw: dict, prompt: str) -> list:
    rows = []
    try:
        result  = raw["tasks"][0]["result"][0]
        sources = result.get("sources", [])
        if not sources:
            rows.append({"Prompt": prompt, "Rank": "—",
                         "URL": "No sources returned by ChatGPT", "Domain": "", "Title": ""})
        for pos, src in enumerate(sources, start=1):
            rows.append({
                "Prompt": prompt,
                "Rank":   pos,
                "URL":    src.get("url", ""),
                "Domain": src.get("domain", ""),
                "Title":  src.get("title", ""),
            })
    except Exception:
        rows.append({"Prompt": prompt, "Rank": "ERR",
                     "URL": "Parse error – check raw JSON tab", "Domain": "", "Title": ""})
    return rows

# ── Run ───────────────────────────────────────
if run_btn:
    if not api_login or not api_password:
        st.error("⛔ Enter your DataForSEO credentials in the sidebar first.")
        st.stop()

    prompts = [p.strip() for p in prompts_input.strip().splitlines() if p.strip()]
    if not prompts:
        st.warning("⚠️ Please enter at least one prompt.")
        st.stop()

    all_rows  = []
    raw_store = {}
    progress  = st.progress(0, text="Starting…")

    for i, kw in enumerate(prompts):
        with st.spinner(f"Querying ChatGPT for: {kw}"):
            try:
                raw           = call_api(kw, api_login, api_password)
                raw_store[kw] = raw
                all_rows.extend(parse_sources(raw, kw))
            except requests.HTTPError as e:
                st.error(f"❌ HTTP Error for '{kw}': {e}")
            except Exception as e:
                st.error(f"❌ Error for '{kw}': {e}")
        progress.progress((i + 1) / len(prompts), text=f"{i+1}/{len(prompts)} done")

    progress.empty()

    if all_rows:
        df = pd.DataFrame(all_rows)

        st.markdown("---")
        st.subheader("📊 Cited Sources & Rank Position")
        st.caption(f"{len(df)} total citations across {len(prompts)} prompt(s) — 📍 Delhi, India")

        def rank_color(val):
            if val == 1: return "background-color:#d4edda; font-weight:bold; color:#155724"
            if val == 2: return "background-color:#fff3cd; color:#856404"
            if val == 3: return "background-color:#fde8d8; color:#7d3c00"
            return ""

        st.dataframe(
            df.style.applymap(rank_color, subset=["Rank"]),
            use_container_width=True, height=520, hide_index=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name=f"chatgpt_sources_delhi_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # ── Summary per prompt ────────────────────────────
        st.markdown("---")
        st.subheader("📋 Summary by Prompt")
        summary_rows = []
        for prompt in prompts:
            subset = df[df["Prompt"] == prompt]
            top    = subset[subset["Rank"] == 1]["URL"].values
            summary_rows.append({
                "Prompt":          prompt,
                "Total Citations": len(subset),
                "#1 Cited URL":    top[0] if len(top) else "—",
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        with st.expander("🔬 Raw API Response (JSON)"):
            st.json(raw_store)

st.markdown("---")
st.caption("Powered by [DataForSEO ChatGPT LLM Scraper API](https://docs.dataforseo.com) • Streamlit")
