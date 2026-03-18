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

st.subheader("🌐 Your Website")
your_domain = st.text_input(
    "Enter your domain to track its rank",
    placeholder="yoursite.com",
    help="We'll highlight your domain in all results and show its citation rank — or flag 'Not cited'."
)

st.subheader("📝 Your Prompts")
st.caption("One prompt per line.")
prompts_input = st.text_area(
    label="Prompts", height=160,
    placeholder="best CA firm in Delhi\ntop digital marketing agency Delhi NCR",
    label_visibility="collapsed",
)

run_btn = st.button("🚀 Run — Find Cited Sources & Your Rank", type="primary", use_container_width=True)

ENDPOINT = "https://api.dataforseo.com/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced"

def norm_domain(s):
    return s.replace("https://","").replace("http://","").replace("www.","").split("/")[0].lower().strip()

def call_api(keyword, login, password):
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    payload = [{
        "keyword":          keyword,
        "location_name":    "Delhi,India",
        "language_name":    "English",
        "language_code":    "en",
        "force_web_search": True,
        "device":           "desktop",
        "os":               "windows",
    }]
    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=130)
    r.raise_for_status()
    return r.json()

def parse_sources(raw, prompt):
    """
    Correctly parses BOTH sources[] and search_results[] arrays from the API response.
    Per DataForSEO docs the result object contains:
      - sources[]       → type: chat_gpt_source   (inline citation panel)
      - search_results[]→ type: chatgpt_search_result (web search results shown)
    We merge both into one ranked list so nothing is missed.
    """
    rows = []
    try:
        result = raw["tasks"][0]["result"][0]

        # ── 1. sources array (inline citation panel) ──
        sources = result.get("sources") or []
        for pos, src in enumerate(sources, 1):
            rows.append({
                "Prompt":    prompt,
                "Source":    "Citation panel",
                "Rank":      pos,
                "URL":       src.get("url", "").replace("?utm_source=chatgpt.com",""),
                "Domain":    src.get("domain", "").replace("www.",""),
                "Title":     src.get("title", ""),
                "Your Site": False,
            })

        # ── 2. search_results array (web results block) ──
        search_results = result.get("search_results") or []
        for pos, src in enumerate(search_results, 1):
            rows.append({
                "Prompt":    prompt,
                "Source":    "Search results",
                "Rank":      pos,
                "URL":       src.get("url", "").replace("?utm_source=chatgpt.com",""),
                "Domain":    src.get("domain", "").replace("www.",""),
                "Title":     src.get("title", ""),
                "Your Site": False,
            })

        # ── 3. If both empty — show debug info ──────────
        if not rows:
            st.warning(f"⚠️ No sources or search_results returned for: **{prompt}**")
            st.code(f"Raw result keys: {list(result.keys())}", language="json")
            st.json(result)   # show full result so you can debug

    except (KeyError, IndexError) as e:
        st.error(f"Parse error for '{prompt}': {e}")
        st.json(raw)

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
        with st.spinner(f"Querying ChatGPT for: **{kw}**"):
            try:
                raw           = call_api(kw, api_login, api_password)
                raw_store[kw] = raw
                rows          = parse_sources(raw, kw)
                for r in rows:
                    if tracked and norm_domain(r["Domain"]) == tracked:
                        r["Your Site"] = True
                all_rows.extend(rows)
                status_code = raw["tasks"][0].get("status_code")
                status_msg  = raw["tasks"][0].get("status_message","")
                if status_code != 20000:
                    st.warning(f"API warning for '{kw}': [{status_code}] {status_msg}")
            except requests.HTTPError as e:
                st.error(f"❌ HTTP Error for '{kw}': {e}")
                st.json(e.response.json() if e.response else {})
            except Exception as e:
                st.error(f"❌ Error for '{kw}': {e}")
        progress.progress((i + 1) / len(prompts), text=f"{i+1}/{len(prompts)} done")

    progress.empty()

    if all_rows:
        df = pd.DataFrame(all_rows)

        st.markdown("---")

        my_rows        = df[df["Your Site"] == True]
        my_count       = len(my_rows)
        prompts_found  = my_rows["Prompt"].nunique()
        best_rank      = int(my_rows["Rank"].min()) if my_count > 0 else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prompts run",      len(prompts))
        c2.metric("Total citations",  len(df))
        c3.metric("Your site cited",  f"{prompts_found}/{len(prompts)}" if my_count > 0 else "0")
        c4.metric("Your best rank",   f"#{best_rank}" if best_rank else "—")

        if tracked:
            if my_count > 0:
                st.success(f"✅ **{tracked}** cited in **{prompts_found}/{len(prompts)}** prompt(s). Best position: **#{best_rank}**.")
            else:
                st.error(f"❌ **{tracked}** was NOT cited by ChatGPT for any prompt — your competitors are.")

        # ── Full results table ────────────────────────
        st.subheader("📊 All Cited Sources & Rank")

        def style_row(row):
            return ["background-color:#eaf3de"]*len(row) if row["Your Site"] else [""]*len(row)

        def rank_color(val):
            if val == 1: return "background-color:#d4edda;font-weight:bold;color:#155724"
            if val == 2: return "background-color:#fff3cd;color:#856404"
            if val == 3: return "background-color:#fde8d8;color:#7d3c00"
            return ""

        display_df = df[["Prompt","Source","Rank","Domain","URL","Title","Your Site"]].copy()
        display_df["Your Site"] = display_df["Your Site"].apply(lambda x: "✅ YES" if x else "")

        st.dataframe(
            display_df.style.apply(style_row, axis=1).applymap(rank_color, subset=["Rank"]),
            use_container_width=True, height=500, hide_index=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", data=csv,
            file_name=f"chatgpt_sources_delhi_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)

        # ── Your rank summary ─────────────────────────
        if tracked:
            st.markdown("---")
            st.subheader("🎯 Your Site Rank by Prompt")
            summary = []
            for p in prompts:
                rows_p = df[df["Prompt"] == p]
                my_r   = rows_p[rows_p["Your Site"] == True]
                top    = rows_p[rows_p["Rank"] == 1]["URL"].values
                summary.append({
                    "Prompt":       p,
                    "Total cited":  len(rows_p),
                    "Your rank":    f"#{int(my_r['Rank'].values[0])}" if len(my_r) > 0 else "❌ Not cited",
                    "#1 cited URL": top[0] if len(top) else "—",
                })
            def color_rank(val):
                if isinstance(val, str) and val.startswith("#"):
                    n = int(val[1:])
                    if n == 1:  return "color:#155724;font-weight:bold"
                    if n <= 3:  return "color:#856404"
                    return "color:#7d3c00"
                if "Not cited" in str(val): return "color:#721c24;font-weight:bold"
                return ""
            st.dataframe(
                pd.DataFrame(summary).style.applymap(color_rank, subset=["Your rank"]),
                use_container_width=True, hide_index=True
            )

        # ── Raw API JSON for full debugging ──────────
        with st.expander("🔬 Raw API Response (JSON) — use this to debug missing sources"):
            st.json(raw_store)

st.markdown("---")
st.caption("Powered by [DataForSEO ChatGPT LLM Scraper API](https://docs.dataforseo.com) • Streamlit")
