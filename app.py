import streamlit as st
import requests
import base64
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="ChatGPT Source Rank Tracker – Delhi", page_icon="🎯", layout="wide")

st.title("🎯 ChatGPT Source Rank Tracker")
st.markdown("**📍 Delhi, India** — Enter your prompts, see which URLs ChatGPT cites & where YOUR site ranks.")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ API Credentials")
    st.markdown("Get from [DataForSEO Dashboard](https://app.dataforseo.com/api-access)")
    api_login    = st.text_input("Login (email)", placeholder="you@example.com")
    api_password = st.text_input("Password", type="password")
    st.markdown("---")
    st.markdown("**📍 Location:** Delhi, India")
    st.markdown("**🤖 Engine:** ChatGPT + Web Search")
    st.markdown("**💰 Cost:** ~$0.004 per prompt")

# ── Your website input ────────────────────────
st.subheader("🌐 Your Website")
your_domain = st.text_input(
    "Enter your domain to track its rank",
    placeholder="yoursite.com  (e.g. cleartax.in)",
    help="The app will highlight your domain in all results and show your citation rank — or flag it as 'Not cited'."
)

st.subheader("📝 Your Prompts")
st.caption("One prompt per line. ChatGPT will be queried for each — Delhi targeted.")
prompts_input = st.text_area(
    label="Prompts",
    height=160,
    placeholder="best CA firm in Delhi\ntop digital marketing agency Delhi NCR\nbest real estate developer South Delhi",
    label_visibility="collapsed",
)

run_btn = st.button("🚀 Run — Find Cited Sources & Your Rank", type="primary", use_container_width=True)

ENDPOINT = "https://api.dataforseo.com/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced"

def norm_domain(s):
    return s.replace("https://","").replace("http://","").replace("www.","").split("/")[0].lower().strip()

def call_api(keyword, login, password):
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    payload = [{"keyword": keyword, "location_name": "Delhi,India", "language_name": "English", "force_web_search": True}]
    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=130)
    r.raise_for_status()
    return r.json()

def parse_sources(raw, prompt):
    rows = []
    try:
        sources = raw["tasks"][0]["result"][0].get("sources", [])
        if not sources:
            rows.append({"Prompt": prompt, "Rank": None, "URL": "No sources returned", "Domain": "", "Title": "", "Your Site": False})
        for pos, src in enumerate(sources, 1):
            rows.append({
                "Prompt":    prompt,
                "Rank":      pos,
                "URL":       src.get("url", ""),
                "Domain":    src.get("domain", ""),
                "Title":     src.get("title", ""),
                "Your Site": False,
            })
    except Exception:
        rows.append({"Prompt": prompt, "Rank": None, "URL": "Parse error", "Domain": "", "Title": "", "Your Site": False})
    return rows

if run_btn:
    if not api_login or not api_password:
        st.error("⛔ Enter your DataForSEO credentials in the sidebar.")
        st.stop()

    prompts = [p.strip() for p in prompts_input.strip().splitlines() if p.strip()]
    if not prompts:
        st.warning("⚠️ Please enter at least one prompt.")
        st.stop()

    tracked = norm_domain(your_domain) if your_domain.strip() else ""

    all_rows  = []
    raw_store = {}
    progress  = st.progress(0, text="Starting…")

    for i, kw in enumerate(prompts):
        with st.spinner(f"Querying ChatGPT: {kw}"):
            try:
                raw           = call_api(kw, api_login, api_password)
                raw_store[kw] = raw
                rows          = parse_sources(raw, kw)
                for r in rows:
                    if tracked and norm_domain(r["Domain"]) == tracked:
                        r["Your Site"] = True
                all_rows.extend(rows)
            except Exception as e:
                st.error(f"❌ Error for '{kw}': {e}")
        progress.progress((i + 1) / len(prompts), text=f"{i+1}/{len(prompts)} done")

    progress.empty()

    if all_rows:
        df = pd.DataFrame(all_rows)

        st.markdown("---")

        # ── Headline metrics ──────────────────────────
        my_rows   = df[df["Your Site"] == True]
        my_count  = len(my_rows)
        prompts_found = my_rows["Prompt"].nunique()
        best_rank = int(my_rows["Rank"].min()) if my_count > 0 else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prompts run",       len(prompts))
        c2.metric("Total citations",   len(df))
        c3.metric("Your site cited",   f"{prompts_found}/{len(prompts)}" if my_count > 0 else "0")
        c4.metric("Your best rank",    f"#{best_rank}" if best_rank else "—")

        # ── Your site alert ───────────────────────────
        if tracked:
            if my_count > 0:
                st.success(f"✅ **{tracked}** was cited in **{prompts_found}/{len(prompts)}** prompt(s). Best position: **#{best_rank}**.")
            else:
                st.error(f"❌ **{tracked}** was **not cited** by ChatGPT for any of these prompts — your competitors are.")

        # ── Full results table ────────────────────────
        st.subheader("📊 All Cited Sources & Rank")

        def style_row(row):
            if row["Your Site"]:
                return ["background-color: #eaf3de"] * len(row)
            return [""] * len(row)

        def rank_color(val):
            if val == 1: return "background-color:#d4edda;font-weight:bold;color:#155724"
            if val == 2: return "background-color:#fff3cd;color:#856404"
            if val == 3: return "background-color:#fde8d8;color:#7d3c00"
            return ""

        display_df = df[["Prompt", "Rank", "Domain", "URL", "Title", "Your Site"]].copy()
        display_df["Your Site"] = display_df["Your Site"].apply(lambda x: "✅ YES" if x else "")

        styled = display_df.style\
            .apply(style_row, axis=1)\
            .applymap(rank_color, subset=["Rank"])

        st.dataframe(styled, use_container_width=True, height=500, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", data=csv,
            file_name=f"chatgpt_sources_delhi_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)

        # ── Your rank by prompt ───────────────────────
        st.markdown("---")
        st.subheader("🎯 Your Site Rank by Prompt")
        summary = []
        for p in prompts:
            rows_p  = df[df["Prompt"] == p]
            my_r    = rows_p[rows_p["Your Site"] == True]
            top_url = rows_p[rows_p["Rank"] == 1]["URL"].values
            summary.append({
                "Prompt":        p,
                "Total cited":   len(rows_p),
                "Your rank":     f"#{int(my_r['Rank'].values[0])}" if len(my_r) > 0 else "Not cited",
                "#1 cited URL":  top_url[0] if len(top_url) else "—",
            })
        sum_df = pd.DataFrame(summary)

        def color_rank(val):
            if isinstance(val, str) and val.startswith("#"):
                n = int(val[1:])
                if n == 1: return "color:#155724;font-weight:bold"
                if n <= 3: return "color:#856404"
                return "color:#7d3c00"
            if val == "Not cited": return "color:#721c24;font-weight:bold"
            return ""

        st.dataframe(
            sum_df.style.applymap(color_rank, subset=["Your rank"]),
            use_container_width=True, hide_index=True
        )

        with st.expander("🔬 Raw API Response (JSON)"):
            st.json(raw_store)

st.markdown("---")
st.caption("Powered by [DataForSEO ChatGPT LLM Scraper API](https://docs.dataforseo.com) • Streamlit")
