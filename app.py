import streamlit as st
import requests
import base64
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="ChatGPT Source Rank Tracker – India/Delhi", page_icon="🎯", layout="wide")

st.title("🎯 ChatGPT Source Rank Tracker")
st.markdown("**📍 India (Delhi targeted)** — Enter prompts → see which URLs ChatGPT cites & where YOUR site ranks.")
st.markdown("---")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ API Credentials")
    st.markdown("Get from [DataForSEO Dashboard](https://app.dataforseo.com/api-access)")
    api_login    = st.text_input("Login (email)", placeholder="you@example.com")
    api_password = st.text_input("Password", type="password")
    st.markdown("---")
    st.markdown("**📍 Location:** India (country-level — confirmed supported)")
    st.markdown("**🌐 Language:** English")
    st.markdown("**🤖 Engine:** ChatGPT + Web Search")
    st.markdown("**💰 Cost:** ~$0.004 per prompt")
    st.markdown("---")
    st.info(
        "**Why India and not Delhi city?**\n\n"
        "DataForSEO's ChatGPT LLM Scraper only supports country-level "
        "location codes. Delhi city code (1007765) returns a 40501 error. "
        "India country code (2356) is confirmed working. "
        "Add 'Delhi' to your prompts for city-specific results."
    )

# ── Inputs ────────────────────────────────────────────────────────────────────
st.subheader("🌐 Your Website")
your_domain = st.text_input(
    "Enter your domain to track its rank",
    placeholder="yoursite.com",
    help="We'll highlight your domain in all results and show its citation rank — or flag 'Not cited'."
)

st.subheader("📝 Your Prompts")
st.caption("One prompt per line. Tip: include 'Delhi' in prompts for city-specific results e.g. 'best CA firm in Delhi'")
prompts_input = st.text_area(
    label="Prompts", height=160,
    placeholder="best aluminium window manufacturers in Delhi\ntop acoustic glass window companies in Delhi\naluminium doors and windows myths and facts",
    label_visibility="collapsed",
)

run_btn = st.button("🚀 Run — Find Cited Sources & Your Rank", type="primary", use_container_width=True)

# ── API Setup ─────────────────────────────────────────────────────────────────
ENDPOINT = "https://api.dataforseo.com/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced"

# VERIFIED from official DataForSEO docs:
# Confirmed working payload format (from docs example):
#   { "language_code": "en", "location_code": 2840, "keyword": "...", "force_web_search": true }
# India country-level location_code = 2356
# Delhi city-level code 1007765 = NOT supported (returns 40501)
INDIA_LOCATION_CODE = 2356

def norm_domain(s: str) -> str:
    return (s or "").replace("https://","").replace("http://","") \
                    .replace("www.","").split("/")[0].split("?")[0].lower().strip()

def call_api(keyword: str, login: str, password: str) -> dict:
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json",
    }
    # EXACT payload format confirmed by official DataForSEO docs:
    # https://docs.dataforseo.com/v3/ai_optimization-chat_gpt-llm_scraper-live-advanced/
    payload = [{
        "language_code":    "en",
        "location_code":    INDIA_LOCATION_CODE,
        "keyword":          keyword,
        "force_web_search": True,
    }]
    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=130)
    r.raise_for_status()
    return r.json()

def parse_sources(raw: dict, prompt: str) -> tuple:
    """
    Verified response structure from official DataForSEO docs:
    tasks[0]
      └── result[0]
            ├── search_results[]  → type: chatgpt_search_result
            └── sources[]         → type: chat_gpt_source
    """
    tasks = raw.get("tasks") or []
    if not tasks:
        return [], "No tasks array in response."

    task      = tasks[0]
    task_code = task.get("status_code")
    task_msg  = task.get("status_message", "")

    if task_code != 20000:
        return [], f"Task error [{task_code}]: {task_msg}"

    result_list = task.get("result") or []
    if not result_list:
        return [], f"result is null/empty. Message: {task_msg}"

    result = result_list[0]
    if result is None:
        return [], "result[0] is None."

    rows      = []
    seen_urls = set()
    rank      = 0

    def add(url, domain, title, source_type):
        nonlocal rank
        clean_url = (url or "").replace("?utm_source=chatgpt.com", "").strip()
        clean_dom = norm_domain(domain or clean_url)
        if not clean_url or clean_url in seen_urls:
            return
        seen_urls.add(clean_url)
        rank += 1
        rows.append({
            "Prompt":    prompt,
            "Rank":      rank,
            "Source":    source_type,
            "Domain":    clean_dom,
            "URL":       clean_url,
            "Title":     (title or "").strip(),
            "Your Site": False,
        })

    # Per verified docs — search_results[] comes first, then sources[]
    for s in (result.get("search_results") or []):
        add(s.get("url"), s.get("domain"), s.get("title"), "Search result")

    for s in (result.get("sources") or []):
        add(s.get("url"), s.get("domain"), s.get("title"), "Citation")

    # Fallback: items[] array
    for item in (result.get("items") or []):
        itype = item.get("type", "")
        if "source" in itype or "search" in itype:
            label = "Citation" if "source" in itype else "Search result"
            add(item.get("url"), item.get("domain"), item.get("title"), label)

    if not rows:
        return [], (
            f"API returned 20000 OK but no sources found. "
            f"Result keys: {list(result.keys())}. "
            f"Check Raw JSON expander below."
        )

    return rows, ""


# ── Run ───────────────────────────────────────────────────────────────────────
if run_btn:
    if not api_login or not api_password:
        st.error("⛔ Enter your DataForSEO credentials in the sidebar.")
        st.stop()

    prompts = [p.strip() for p in prompts_input.strip().splitlines() if p.strip()]
    if not prompts:
        st.warning("⚠️ Please enter at least one prompt.")
        st.stop()

    tracked   = norm_domain(your_domain)
    all_rows  = []
    raw_store = {}
    progress  = st.progress(0, text="Starting…")

    for i, kw in enumerate(prompts):
        with st.spinner(f"Querying ChatGPT for: **{kw}**"):
            try:
                raw           = call_api(kw, api_login, api_password)
                raw_store[kw] = raw
                rows, err     = parse_sources(raw, kw)

                if err:
                    st.warning(f"⚠️ '{kw}' — {err}")
                else:
                    for r in rows:
                        if tracked and norm_domain(r["Domain"]) == tracked:
                            r["Your Site"] = True
                    all_rows.extend(rows)
                    st.success(f"✅ **{kw}** → {len(rows)} source(s) found")

            except requests.HTTPError as e:
                try:    body = e.response.json()
                except: body = e.response.text
                st.error(f"❌ HTTP {e.response.status_code} for '{kw}': {body}")
            except Exception as e:
                st.error(f"❌ Error for '{kw}': {type(e).__name__}: {e}")

        progress.progress((i + 1) / len(prompts), text=f"{i+1}/{len(prompts)} done")

    progress.empty()

    with st.expander("🔬 Raw API Response — expand to debug if sources are missing"):
        st.json(raw_store)

    if not all_rows:
        st.info("No results to display. Expand the Raw JSON expander above for details.")
        st.stop()

    df = pd.DataFrame(all_rows)
    st.markdown("---")

    # ── Metrics ───────────────────────────────────────────────────────────────
    my_rows       = df[df["Your Site"] == True]
    my_count      = len(my_rows)
    prompts_found = int(my_rows["Prompt"].nunique()) if my_count > 0 else 0
    best_rank     = int(my_rows["Rank"].min()) if my_count > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prompts run",     len(prompts))
    c2.metric("Total citations", len(df))
    c3.metric("Your site cited", f"{prompts_found}/{len(prompts)}" if my_count > 0 else "0")
    c4.metric("Your best rank",  f"#{best_rank}" if best_rank else "—")

    if tracked:
        if my_count > 0:
            st.success(f"✅ **{tracked}** cited in **{prompts_found}/{len(prompts)}** prompt(s). Best rank: **#{best_rank}**.")
        else:
            st.error(f"❌ **{tracked}** was NOT cited by ChatGPT for any of these prompts.")

    # ── Full table ────────────────────────────────────────────────────────────
    st.subheader("📊 All Cited Sources & Rank")

    def style_row(row):
        return ["background-color:#eaf3de"] * len(row) if row["Your Site"] else [""] * len(row)

    def rank_color(val):
        try:
            v = int(val)
            if v == 1: return "background-color:#d4edda;font-weight:bold;color:#155724"
            if v == 2: return "background-color:#fff3cd;color:#856404"
            if v == 3: return "background-color:#fde8d8;color:#7d3c00"
        except: pass
        return ""

    disp = df[["Prompt","Rank","Source","Domain","URL","Title","Your Site"]].copy()
    disp["Your Site"] = disp["Your Site"].apply(lambda x: "✅ YES" if x else "")

    st.dataframe(
        disp.style.apply(style_row, axis=1).applymap(rank_color, subset=["Rank"]),
        use_container_width=True, height=500, hide_index=True
    )

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV", data=csv,
        file_name=f"chatgpt_sources_india_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv", use_container_width=True
    )

    # ── Your rank by prompt ───────────────────────────────────────────────────
    if tracked:
        st.markdown("---")
        st.subheader("🎯 Your Site Rank by Prompt")
        summary = []
        for p in prompts:
            rp   = df[df["Prompt"] == p]
            my_r = rp[rp["Your Site"] == True]
            top  = rp[rp["Rank"] == 1]["URL"].values
            summary.append({
                "Prompt":       p,
                "Total cited":  len(rp),
                "Your rank":    f"#{int(my_r['Rank'].values[0])}" if len(my_r) > 0 else "❌ Not cited",
                "#1 cited URL": top[0] if len(top) else "—",
            })

        def color_rank(val):
            v = str(val)
            if v.startswith("#"):
                try:
                    n = int(v[1:])
                    if n == 1: return "color:#155724;font-weight:bold"
                    if n <= 3: return "color:#856404"
                    return "color:#7d3c00"
                except: pass
            if "Not cited" in v: return "color:#721c24;font-weight:bold"
            return ""

        st.dataframe(
            pd.DataFrame(summary).style.applymap(color_rank, subset=["Your rank"]),
            use_container_width=True, hide_index=True
        )

st.markdown("---")
st.caption("Powered by [DataForSEO ChatGPT LLM Scraper API](https://docs.dataforseo.com) • Streamlit")
