import streamlit as st
import requests
import base64
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="ChatGPT Source Rank Tracker – Delhi", page_icon="🎯", layout="wide")

st.title("🎯 ChatGPT Source Rank Tracker")
st.markdown("**📍 Delhi, India** — Enter your prompts, see which URLs ChatGPT cites & where YOUR site ranks.")
st.markdown("---")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ API Credentials")
    st.markdown("Get from [DataForSEO Dashboard](https://app.dataforseo.com/api-access)")
    api_login    = st.text_input("Login (email)", placeholder="you@example.com")
    api_password = st.text_input("Password", type="password")
    st.markdown("---")
    st.markdown("**📍 Location:** Delhi, India")
    st.markdown("**🤖 Engine:** ChatGPT + Web Search")
    st.markdown("**💰 Cost:** ~$0.004 per prompt")

# ── Inputs ────────────────────────────────────────────────────────────────────
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

# ── Constants ─────────────────────────────────────────────────────────────────
ENDPOINT = "https://api.dataforseo.com/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced"
DELHI_LOCATION_CODE = 1007765   # Delhi, India city-level code

def norm_domain(s: str) -> str:
    return (s or "").replace("https://","").replace("http://","") \
                    .replace("www.","").split("/")[0].split("?")[0].lower().strip()

# ── API call ──────────────────────────────────────────────────────────────────
def call_api(keyword: str, login: str, password: str) -> dict:
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json",
    }
    payload = [{
        "keyword":           keyword,
        "location_code":     DELHI_LOCATION_CODE,
        "language_code":     "en",
        "force_web_search":  True,
        "device":            "desktop",
        "os":                "windows",
    }]
    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=130)
    r.raise_for_status()
    return r.json()

# ── Parser — built from official DataForSEO docs response schema ──────────────
def parse_sources(raw: dict, prompt: str) -> tuple[list[dict], str]:
    """
    Returns (rows, error_message).
    Based on official docs the response is:
      raw["tasks"][0]["result"][0]["items"]   ← list of typed elements
      raw["tasks"][0]["result"][0]["sources"] ← citation panel (may be None)
      raw["tasks"][0]["result"][0]["search_results"] ← web search block (may be None)

    Each item in items[] has a "type" field:
      - "chatgpt_search_result"  → web search result row
      - "chat_gpt_source"        → inline citation

    We extract from ALL three locations and deduplicate by URL.
    """
    rows = []

    # ── Step 1: safely navigate to the task ──────────────────────────────────
    tasks = raw.get("tasks")
    if not tasks:
        return [], f"API returned no tasks. Full response: {raw}"

    task = tasks[0]
    task_status  = task.get("status_code")
    task_message = task.get("status_message", "")

    if task_status != 20000:
        return [], f"Task error [{task_status}]: {task_message}"

    # ── Step 2: safely navigate to result ────────────────────────────────────
    result_list = task.get("result")
    if not result_list:
        return [], f"Task returned no result (result=None or empty). status={task_status} msg={task_message}"

    result = result_list[0]
    if result is None:
        return [], "result[0] is None — ChatGPT returned an empty response for this prompt."

    seen_urls = set()
    rank_counter = 0

    def add_row(url, domain, title, source_type):
        nonlocal rank_counter
        clean_url = (url or "").replace("?utm_source=chatgpt.com", "").strip()
        clean_dom = norm_domain(domain or clean_url)
        if not clean_url or clean_url in seen_urls:
            return
        seen_urls.add(clean_url)
        rank_counter += 1
        rows.append({
            "Prompt":    prompt,
            "Rank":      rank_counter,
            "Source":    source_type,
            "URL":       clean_url,
            "Domain":    clean_dom,
            "Title":     (title or "").strip(),
            "Your Site": False,
        })

    # ── Step 3a: items[] array (primary — typed elements) ────────────────────
    for item in (result.get("items") or []):
        itype = item.get("type", "")
        if itype in ("chatgpt_search_result", "chat_gpt_source"):
            add_row(item.get("url"), item.get("domain"), item.get("title"), "search_results" if "search" in itype else "citation")

    # ── Step 3b: top-level sources[] (citation panel) ────────────────────────
    for src in (result.get("sources") or []):
        add_row(src.get("url"), src.get("domain"), src.get("title"), "citation")

    # ── Step 3c: top-level search_results[] ──────────────────────────────────
    for src in (result.get("search_results") or []):
        add_row(src.get("url"), src.get("domain"), src.get("title"), "search_results")

    if not rows:
        # Show what keys actually came back so we can debug further
        return [], (
            f"No sources found in items[], sources[], or search_results[]. "
            f"Result keys present: {list(result.keys())}. "
            f"Tip: expand the raw JSON expander below to inspect the full response."
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
                    st.warning(f"⚠️ **{kw}** → {err}")
                else:
                    # Mark your site
                    for r in rows:
                        if tracked and norm_domain(r["Domain"]) == tracked:
                            r["Your Site"] = True
                    all_rows.extend(rows)
                    st.success(f"✅ **{kw}** → {len(rows)} source(s) found")

            except requests.HTTPError as e:
                body = {}
                try: body = e.response.json()
                except: pass
                st.error(f"❌ HTTP {e.response.status_code} for '{kw}': {body}")
            except Exception as e:
                st.error(f"❌ Unexpected error for '{kw}': {type(e).__name__}: {e}")

        progress.progress((i + 1) / len(prompts), text=f"{i+1}/{len(prompts)} done")

    progress.empty()

    # ── Always show raw JSON so user can debug ────────────────────────────────
    with st.expander("🔬 Raw API Response — expand if sources are missing"):
        st.json(raw_store)

    if not all_rows:
        st.info("No results to display. Check the raw JSON expander above for clues.")
        st.stop()

    df = pd.DataFrame(all_rows)

    st.markdown("---")

    # ── Metrics ───────────────────────────────────────────────────────────────
    my_rows       = df[df["Your Site"] == True]
    my_count      = len(my_rows)
    prompts_found = my_rows["Prompt"].nunique()
    best_rank     = int(my_rows["Rank"].min()) if my_count > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prompts run",     len(prompts))
    c2.metric("Total citations", len(df))
    c3.metric("Your site cited", f"{prompts_found}/{len(prompts)}" if my_count > 0 else "0")
    c4.metric("Your best rank",  f"#{best_rank}" if best_rank else "—")

    if tracked:
        if my_count > 0:
            st.success(f"✅ **{tracked}** cited in **{prompts_found}/{len(prompts)}** prompt(s). Best position: **#{best_rank}**.")
        else:
            st.error(f"❌ **{tracked}** was NOT cited by ChatGPT for any of these prompts.")

    # ── Full results table ────────────────────────────────────────────────────
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

    display_df = df[["Prompt","Rank","Source","Domain","URL","Title","Your Site"]].copy()
    display_df["Your Site"] = display_df["Your Site"].apply(lambda x: "✅ YES" if x else "")

    st.dataframe(
        display_df.style.apply(style_row, axis=1).applymap(rank_color, subset=["Rank"]),
        use_container_width=True, height=500, hide_index=True
    )

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV", data=csv,
        file_name=f"chatgpt_sources_delhi_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv", use_container_width=True
    )

    # ── Your rank by prompt ───────────────────────────────────────────────────
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
