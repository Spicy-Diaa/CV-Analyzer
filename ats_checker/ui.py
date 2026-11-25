"""Streamlit rendering of the ATS report (green = good, red = problem, orange = needs improvement)."""
from html import escape

import streamlit as st

from .report import COLORS, badge, build_html_report


# ---------------------------------------------------------------- styling
_CSS = """
<style>
.hp-score-card{border:1px solid #e6e8ec;border-radius:16px;padding:20px 24px;background:#fff;
  box-shadow:0 2px 10px rgba(0,0,0,.04);margin-bottom:14px}
.hp-score-top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.hp-score-num{font-size:56px;font-weight:700;line-height:1}
.hp-score-max{font-size:22px;color:#888}
.hp-score-label{font-size:18px;font-weight:600}
.hp-bar{height:12px;border-radius:999px;background:#eceef2;overflow:hidden;margin-top:14px}
.hp-bar>div{height:100%;border-radius:999px}
.hp-counters{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 18px}
.hp-counter{flex:1 1 140px;border:1px solid #e6e8ec;border-radius:14px;padding:12px 16px;background:#fff;
  border-top-width:4px}
.hp-counter .n{font-size:28px;font-weight:700;line-height:1.1}
.hp-counter .t{font-size:13px;color:#666}
div[data-testid="stExpander"]{border:1px solid #e6e8ec !important;border-radius:14px !important;
  background:#fff;margin-bottom:10px;box-shadow:0 1px 6px rgba(0,0,0,.03)}
div[data-testid="stExpander"] summary{padding:14px 16px;font-weight:600}
@media (max-width:640px){.hp-score-num{font-size:44px}}
</style>
"""


# ---------------------------------------------------------------- helpers
def _download(result):
    html = build_html_report(result)
    kwargs = dict(label="⬇️ Download ATS report (HTML - open it and print to PDF)", data=html,
                  file_name="hire_path_ats_report.html", mime="text/html")
    try:  # on_click="ignore" keeps the page from re-running (and hiding the results) after download
        st.download_button(on_click="ignore", **kwargs)
    except TypeError:  # older Streamlit versions
        st.download_button(**kwargs)


def _rows(rows, ok_values):
    for name, status, detail, fix in rows:
        c1, c2, c3 = st.columns([2, 1.4, 5])
        c1.markdown(f"**{escape(name)}**")
        c2.markdown(badge(status), unsafe_allow_html=True)
        text = escape(detail)
        if status not in ok_values and fix:
            text += f"<br><span style='color:{COLORS['Needs Improvement']}'>💡 {escape(fix)}</span>"
        c3.markdown(text, unsafe_allow_html=True)


# (title, icon) in display order
_GROUPS = [
    ("Personal Information", "📋"),
    ("Professional Profile", "📚"),
    ("Education & Experience", "🎓"),
    ("Skills", "🛠️"),
    ("Additional Information", "🚀"),
]


def _group_of(label):
    """Decide which card an item belongs to, based on its label. Unknown labels go to Additional Information."""
    l = label.lower()
    if any(k in l for k in ("name", "email", "phone", "location")):
        return "Personal Information"
    if "summary" in l or "profile" in l:
        return "Professional Profile"
    if "education" in l or "experience" in l:
        return "Education & Experience"
    if "skill" in l:
        return "Skills"
    return "Additional Information"


def _group_status(items):
    """Return the text shown on the right side of the card title."""
    total = len(items)
    found = sum(1 for i in items if i["status"] == "Found")
    if found == total:
        return f"✅ Found {found}/{total}"
    if all(i["status"] == "Missing" for i in items):
        return f"❌ Missing 0/{total}"
    return f"🟠 Needs Improvement · Found {found}/{total}"


def _score_color(score):
    return COLORS["Good"] if score >= 70 else COLORS["Needs Improvement"] if score >= 50 else COLORS["Problem"]


def _counter(n, title, color):
    return (f"<div class='hp-counter' style='border-top-color:{color}'>"
            f"<div class='n' style='color:{color}'>{n}</div><div class='t'>{title}</div></div>")


def _render_cards(items):
    grouped = {title: [] for title, _ in _GROUPS}
    for i in items:
        grouped[_group_of(i["label"])].append(i)

    for title, icon in _GROUPS:
        group_items = grouped[title]
        if not group_items:
            continue
        with st.expander(f"{icon} {title}  ·  {_group_status(group_items)}", expanded=False):
            _rows([(i["label"], i["status"], i["detail"], i["fix"]) for i in group_items], {"Found"})


# ---------------------------------------------------------------- main
def render_ats_report(result):
    if result.get("error"):
        st.error(result["error"])
        if result.get("is_scanned"):
            st.info("Tip: if you can copy text from your CV when you open it in a PDF viewer, it is ATS-readable. "
                    "If you cannot, ATS software will see an empty page.")
        return

    st.markdown(_CSS, unsafe_allow_html=True)
    s = result["score"]
    color = _score_color(s["score"])

    st.subheader("ATS Analysis Results")

    # Header: score + progress bar
    st.markdown(
        f"<div class='hp-score-card'>"
        f"<div class='hp-score-top'><span class='hp-score-num' style='color:{color}'>{s['score']}</span>"
        f"<span class='hp-score-max'>/100</span>"
        f"<span class='hp-score-label' style='color:{color}'>{escape(s['label'])}</span></div>"
        f"<div class='hp-bar'><div style='width:{max(0, min(100, s['score']))}%;background:{color}'></div></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Counters
    found = sum(1 for i in result["items"] if i["status"] == "Found")
    miss = sum(1 for i in result["items"] if i["status"] == "Missing")
    imp = sum(1 for i in result["items"] if i["status"] == "Needs Improvement")
    st.markdown(
        "<div class='hp-counters'>"
        + _counter(found, "Found", COLORS["Good"])
        + _counter(imp, "Needs Improvement", COLORS["Needs Improvement"])
        + _counter(miss, "Missing", COLORS["Problem"])
        + "</div>",
        unsafe_allow_html=True,
    )

    # Score breakdown (kept from the original)
    with st.expander("📊 Score breakdown", expanded=False):
        for b in s["breakdown"]:
            st.markdown(f"**{escape(b['category'])}** — {b['earned']} / {b['max']}")
            st.progress(b["earned"] / b["max"] if b["max"] else 0)
    st.caption(s["disclaimer"])

    tab1, tab2, tab3 = st.tabs(["📋 Information check", "🛠️ Formatting analysis", "💡 Recommendations"])
    with tab1:
        _render_cards(result["items"])
    with tab2:
        _rows([(c["name"], c["status"], c["detail"], c["fix"]) for c in result["checks"]], {"Good", "Skipped"})
    with tab3:
        icons = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
        for r in result["recommendations"]:
            st.markdown(f"{icons[r['priority']]} **{escape(r['title'])}** *({r['priority']} priority)*  \n{escape(r['detail'])}")
    _download(result)
