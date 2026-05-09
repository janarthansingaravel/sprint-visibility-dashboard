import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import json
import base64
from collections import defaultdict

# ──────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────
st.set_page_config(
    page_title="PI Sprint Command Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ──────────────────────────────────────────
# GLOBAL CSS
# ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── BASE ── */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #080c14 !important;
    color: #e2e8f0 !important;
}
.stApp { background: #080c14; }
.block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }

/* ── HIDE STREAMLIT CHROME ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: #0d1424 !important;
    border-right: 1px solid #1a2640 !important;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }

/* ── BUTTONS ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid #1a2640 !important;
    color: #94a3b8 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    border-radius: 4px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    border-color: #3b82f6 !important;
    color: #3b82f6 !important;
    background: rgba(59,130,246,0.08) !important;
}

/* ── TEXT INPUT ── */
.stTextInput > div > div > input {
    background: #0d1424 !important;
    border: 1px solid #1a2640 !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    border-radius: 4px !important;
}
.stTextInput > label { color: #64748b !important; font-size: 11px !important; }

/* ── SELECTBOX ── */
.stSelectbox > div > div {
    background: #0d1424 !important;
    border: 1px solid #1a2640 !important;
    color: #e2e8f0 !important;
}

/* ── DATAFRAME ── */
.stDataFrame { border: 1px solid #1a2640 !important; border-radius: 6px !important; }

/* ── METRICS ── */
[data-testid="stMetric"] {
    background: #0d1424;
    border: 1px solid #1a2640;
    border-radius: 8px;
    padding: 1rem;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
}

/* ── DIVIDER ── */
hr { border-color: #1a2640 !important; }

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: #0d1424 !important;
    border: 1px solid #1a2640 !important;
    border-radius: 6px !important;
    font-size: 12px !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #080c14; }
::-webkit-scrollbar-thumb { background: #1a2640; border-radius: 3px; }

/* ── CARD BASE ── */
.dash-card {
    background: #0d1424;
    border: 1px solid #1a2640;
    border-radius: 10px;
    padding: 20px;
    height: 100%;
}

/* ── TEAM CARD COLORS ── */
.team-critical { border-color: #ef4444 !important; border-width: 2px !important; }
.team-atrisk   { border-color: #f97316 !important; border-width: 2px !important; }
.team-watch    { border-color: #f59e0b !important; border-width: 2px !important; }
.team-healthy  { border-color: #10b981 !important; border-width: 2px !important; }
.team-nodata   { border-color: #374151 !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────
TEAMS = [
    "Echo Engineers",
    "Code Commanders",
    "Beta Brigade",
    "Gamma Guardians",
    "Hyper Hackers"
]

TEAM_AVATARS = {
    "Echo Engineers":   "⚡",
    "Code Commanders":  "🛡️",
    "Beta Brigade":     "🔥",
    "Gamma Guardians":  "🌀",
    "Hyper Hackers":    "💥"
}

COMPLETED_STATES  = ["Done", "Resolved", "Dev Completed"]
INPROGRESS_STATES = ["In Progress", "Scheduled"]
WORKING_HRS_LEFT  = 40  # updated dynamically

# ──────────────────────────────────────────
# AZURE DEVOPS API
# ──────────────────────────────────────────
class AzureDevOpsClient:
    def __init__(self, org_url: str, project: str, pat: str):
        self.org_url = org_url.rstrip("/")
        self.project = project
        token = base64.b64encode(f":{pat}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json"
        }

    def _get(self, url: str, params: dict = None):
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {e}")
            return None

    def _post(self, url: str, body: dict):
        try:
            r = requests.post(url, headers=self.headers, json=body, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {e}")
            return None

    def get_current_sprint(self, team: str) -> dict | None:
        """Get the current active sprint for a team."""
        url = f"{self.org_url}/{self.project}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations"
        data = self._get(url, params={"$timeframe": "current", "api-version": "7.0"})
        if data and data.get("value"):
            return data["value"][0]
        return None

    def get_sprint_work_items(self, team: str, iteration_id: str) -> list:
        """Get all work item IDs in a sprint."""
        url = f"{self.org_url}/{self.project}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations/{iteration_id}/workitems"
        data = self._get(url, params={"api-version": "7.0"})
        if not data:
            return []
        return [wi["id"] for wi in data.get("workItemRelations", [])
                if wi.get("rel") is None or wi["rel"] in ["System.LinkTypes.Hierarchy-Forward", None]]

    def get_work_items_batch(self, ids: list) -> list:
        """Fetch work item details in batches of 200."""
        if not ids:
            return []
        fields = [
            "System.Id", "System.Title", "System.WorkItemType",
            "System.State", "System.AssignedTo", "System.TeamProject",
            "Microsoft.VSTS.Scheduling.OriginalEstimate",
            "Microsoft.VSTS.Scheduling.CompletedWork",
            "Microsoft.VSTS.Scheduling.RemainingWork",
            "Microsoft.VSTS.Common.Priority",
            "System.Tags", "System.IterationPath",
            "System.AreaPath", "System.Parent",
            "Microsoft.VSTS.Common.Activity",
            "System.CreatedDate", "Microsoft.VSTS.Scheduling.StartDate",
            "Microsoft.VSTS.Scheduling.TargetDate"
        ]
        all_items = []
        for i in range(0, len(ids), 200):
            batch = ids[i:i+200]
            url = f"{self.org_url}/_apis/wit/workitemsbatch"
            body = {"ids": batch, "fields": fields}
            data = self._post(url + "?api-version=7.0", body)
            if data:
                all_items.extend(data.get("value", []))
        return all_items

    def get_work_item_with_parent(self, item_id: int) -> dict | None:
        """Get a single work item with relations to find parent chain."""
        url = f"{self.org_url}/_apis/wit/workitems/{item_id}"
        return self._get(url, params={"$expand": "relations", "api-version": "7.0"})

    def get_features_for_items(self, parent_ids: list) -> list:
        """Get parent backlog items and their parent features."""
        if not parent_ids:
            return []
        return self.get_work_items_batch(list(set(parent_ids)))

    def run_wiql(self, query: str) -> list:
        """Run a WIQL query and return work item IDs."""
        url = f"{self.org_url}/{self.project}/_apis/wit/wiql"
        data = self._post(url + "?api-version=7.0", {"query": query})
        if data:
            return [wi["id"] for wi in data.get("workItems", [])]
        return []

# ──────────────────────────────────────────
# RISK ENGINE
# ──────────────────────────────────────────
def calculate_working_hours_left(sprint_end: date) -> int:
    today = date.today()
    if today > sprint_end:
        return 0
    count = 0
    current = today
    while current <= sprint_end:
        if current.weekday() < 5:  # Mon–Fri
            count += 1
        current = date.fromordinal(current.toordinal() + 1)
    return count * 8

def classify_item_risk(item: dict, hrs_left: int) -> tuple[str, list[str]]:
    """Returns (risk_tier, reasons) — 'none' | 'watch' | 'high'"""
    state     = item.get("state", "")
    est       = item.get("original_estimate", 0) or 0
    done      = item.get("completed_work", 0) or 0
    rem       = item.get("remaining_work", 0) or 0
    target_dt = item.get("target_date")

    if state in COMPLETED_STATES:
        return "none", []

    is_ip     = state in INPROGRESS_STATES
    is_todo   = state == "To Do"
    is_onhold = state == "On hold"

    total          = done + rem
    progress_ratio = (done / total) if total > 0 else 0
    risk           = "none"
    reasons        = []

    # ── HIGH RISK ──
    if is_onhold:
        risk = "high"; reasons.append("🔴 Blocked — On Hold")
    if target_dt:
        try:
            td = datetime.strptime(target_dt[:10], "%Y-%m-%d").date()
            sprint_end = item.get("sprint_end")
            if sprint_end and td > sprint_end:
                risk = "high"; reasons.append("🔴 Target date beyond sprint end")
        except: pass
    if is_todo and rem > hrs_left:
        risk = "high"; reasons.append(f"🔴 Not started · {rem}h rem > {hrs_left}h left")
    if state == "Scheduled" and rem > hrs_left:
        risk = "high"; reasons.append(f"🔴 Scheduled · {rem}h rem > {hrs_left}h left")

    # ── WATCH ──
    if risk != "high":
        if is_todo and rem > 4:
            risk = "watch"; reasons.append(f"🟡 Not started · {rem}h remaining")
        if is_ip and progress_ratio < 0.3 and total > 4:
            risk = "watch"; reasons.append(f"🟡 Only {int(progress_ratio*100)}% complete")
        if is_ip and done == 0 and rem > 0:
            risk = "watch"; reasons.append("🟡 In Progress but no hours logged")
        if state == "Scheduled":
            risk = "watch"; reasons.append("🟡 Scheduled — not yet activated")

    return risk, reasons

def classify_overburn(item: dict) -> tuple[bool, float]:
    """Returns (is_overburn, overrun_hours)"""
    state = item.get("state", "")
    est   = item.get("original_estimate", 0) or 0
    done  = item.get("completed_work", 0) or 0
    rem   = item.get("remaining_work", 0) or 0

    if est <= 0:
        return False, 0

    if state in COMPLETED_STATES:
        overrun = done - est
        return overrun > 0, max(overrun, 0)
    elif state in INPROGRESS_STATES:
        projected = done + rem
        overrun   = projected - est
        return overrun > 0, max(overrun, 0)
    return False, 0

def score_team_health(items: list) -> dict:
    """
    Returns team health dict:
    { status, score, high_count, watch_count, overburn_count,
      completion_pct, total_items, done_items, at_risk_features }
    """
    if not items:
        return {"status": "no_data", "score": 0}

    tasks = [i for i in items if i.get("type") == "Task"]
    if not tasks:
        tasks = items

    total     = len(tasks)
    done      = sum(1 for i in tasks if i.get("state") in COMPLETED_STATES)
    high      = sum(1 for i in tasks if i.get("spill_risk") == "high")
    watch     = sum(1 for i in tasks if i.get("spill_risk") == "watch")
    overburns = sum(1 for i in tasks if i.get("is_overburn"))

    completion_pct = round((done / total) * 100) if total > 0 else 0
    overburn_pct   = round((overburns / total) * 100) if total > 0 else 0

    # Score: lower is worse (0–100)
    score = 100
    score -= high   * 15
    score -= watch  * 5
    score -= overburn_pct * 0.5
    score  = max(0, min(100, score))

    if high >= 3 or overburn_pct >= 30:
        status = "critical"
    elif high >= 1 or overburn_pct >= 15:
        status = "atrisk"
    elif watch >= 1 or overburn_pct > 0:
        status = "watch"
    else:
        status = "healthy"

    return {
        "status":         status,
        "score":          int(score),
        "high_count":     high,
        "watch_count":    watch,
        "overburn_count": overburns,
        "completion_pct": completion_pct,
        "total_items":    total,
        "done_items":     done,
        "overburn_pct":   overburn_pct,
    }

# ──────────────────────────────────────────
# DATA LOADER
# ──────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_team_data(org_url: str, project: str, pat: str, team: str) -> dict:
    """Load and enrich sprint data for one team."""
    client = AzureDevOpsClient(org_url, project, pat)

    # 1. Get current sprint
    sprint = client.get_current_sprint(team)
    if not sprint:
        return {"team": team, "error": "No active sprint found", "items": []}

    sprint_name  = sprint.get("name", "")
    sprint_attrs = sprint.get("attributes", {})
    start_str    = sprint_attrs.get("startDate", "")
    end_str      = sprint_attrs.get("finishDate", "")

    sprint_start = datetime.strptime(start_str[:10], "%Y-%m-%d").date() if start_str else None
    sprint_end   = datetime.strptime(end_str[:10],   "%Y-%m-%d").date() if end_str   else None
    hrs_left     = calculate_working_hours_left(sprint_end) if sprint_end else 40

    # 2. Get work item IDs
    iteration_id = sprint.get("id", "")
    wi_ids       = client.get_sprint_work_items(team, iteration_id)
    if not wi_ids:
        return {"team": team, "sprint_name": sprint_name,
                "sprint_start": sprint_start, "sprint_end": sprint_end,
                "items": [], "hrs_left": hrs_left}

    # 3. Get work item details
    raw_items = client.get_work_items_batch(wi_ids)

    # 4. Enrich items
    items        = []
    parent_ids   = set()

    for wi in raw_items:
        f = wi.get("fields", {})
        assignee_field = f.get("System.AssignedTo", {})
        assignee = assignee_field.get("displayName", "Unassigned") if isinstance(assignee_field, dict) else str(assignee_field or "Unassigned")

        item = {
            "id":                wi.get("id"),
            "title":             f.get("System.Title", ""),
            "type":              f.get("System.WorkItemType", ""),
            "state":             f.get("System.State", ""),
            "assignee":          assignee,
            "original_estimate": f.get("Microsoft.VSTS.Scheduling.OriginalEstimate", 0),
            "completed_work":    f.get("Microsoft.VSTS.Scheduling.CompletedWork", 0),
            "remaining_work":    f.get("Microsoft.VSTS.Scheduling.RemainingWork", 0),
            "priority":          f.get("Microsoft.VSTS.Common.Priority", 3),
            "tags":              f.get("System.Tags", ""),
            "activity":          f.get("Microsoft.VSTS.Common.Activity", ""),
            "start_date":        f.get("Microsoft.VSTS.Scheduling.StartDate", ""),
            "target_date":       f.get("Microsoft.VSTS.Scheduling.TargetDate", ""),
            "parent_id":         f.get("System.Parent"),
            "sprint_name":       sprint_name,
            "sprint_start":      sprint_start,
            "sprint_end":        sprint_end,
            "team":              team,
            "url":               f"{org_url}/{project}/_workitems/edit/{wi.get('id')}"
        }

        # Risk classification
        risk, reasons          = classify_item_risk(item, hrs_left)
        is_overburn, overrun   = classify_overburn(item)
        item["spill_risk"]     = risk
        item["spill_reasons"]  = reasons
        item["is_overburn"]    = is_overburn
        item["overrun_hours"]  = overrun

        if item["parent_id"]:
            parent_ids.add(item["parent_id"])
        items.append(item)

    # 5. Load parent (Backlog Items) and grandparent (Features)
    parent_map  = {}
    feature_map = {}

    if parent_ids:
        parents = client.get_work_items_batch(list(parent_ids))
        gp_ids  = set()
        for p in parents:
            f  = p.get("fields", {})
            pid = p.get("id")
            parent_map[pid] = {
                "id":    pid,
                "title": f.get("System.Title", ""),
                "type":  f.get("System.WorkItemType", ""),
                "state": f.get("System.State", ""),
                "parent_id": f.get("System.Parent"),
            }
            if f.get("System.Parent"):
                gp_ids.add(f["System.Parent"])

        if gp_ids:
            grandparents = client.get_work_items_batch(list(gp_ids))
            for gp in grandparents:
                f   = gp.get("fields", {})
                gid = gp.get("id")
                feature_map[gid] = {
                    "id":    gid,
                    "title": f.get("System.Title", ""),
                    "type":  f.get("System.WorkItemType", ""),
                    "state": f.get("System.State", ""),
                }

    # 6. Attach parent/feature to each item
    for item in items:
        pid = item.get("parent_id")
        if pid and pid in parent_map:
            item["backlog_item"]  = parent_map[pid]
            fid = parent_map[pid].get("parent_id")
            if fid and fid in feature_map:
                item["feature"] = feature_map[fid]
            else:
                item["feature"] = None
        else:
            item["backlog_item"] = None
            item["feature"]      = None

    health = score_team_health(items)

    return {
        "team":         team,
        "sprint_name":  sprint_name,
        "sprint_start": sprint_start,
        "sprint_end":   sprint_end,
        "hrs_left":     hrs_left,
        "items":        items,
        "health":       health,
        "parent_map":   parent_map,
        "feature_map":  feature_map,
    }

# ──────────────────────────────────────────
# UI HELPERS
# ──────────────────────────────────────────
STATUS_CONFIG = {
    "critical": {"color": "#ef4444", "bg": "rgba(239,68,68,0.08)",   "border": "#ef4444", "label": "CRITICAL",  "icon": "🔴"},
    "atrisk":   {"color": "#f97316", "bg": "rgba(249,115,22,0.08)",  "border": "#f97316", "label": "AT RISK",   "icon": "🟠"},
    "watch":    {"color": "#f59e0b", "bg": "rgba(245,158,11,0.08)",  "border": "#f59e0b", "label": "WATCH",     "icon": "🟡"},
    "healthy":  {"color": "#10b981", "bg": "rgba(16,185,129,0.08)",  "border": "#10b981", "label": "HEALTHY",   "icon": "🟢"},
    "no_data":  {"color": "#374151", "bg": "rgba(55,65,81,0.08)",    "border": "#374151", "label": "NO DATA",   "icon": "⚫"},
}

def status_badge_html(status: str, size: int = 11) -> str:
    c = STATUS_CONFIG.get(status, STATUS_CONFIG["no_data"])
    return f"""<span style="background:{c['bg']};color:{c['color']};border:1px solid {c['border']};
        border-radius:3px;padding:2px 8px;font-size:{size}px;font-weight:700;
        letter-spacing:1px;font-family:'JetBrains Mono',monospace">{c['icon']} {c['label']}</span>"""

def mini_bar_html(pct: int, color: str, height: int = 5) -> str:
    return f"""<div style="background:#1a2640;border-radius:3px;height:{height}px;overflow:hidden;margin-top:4px">
        <div style="width:{min(pct,100)}%;height:100%;background:{color};border-radius:3px;
             transition:width 0.8s ease"></div></div>"""

def score_ring_html(score: int, color: str, size: int = 60) -> str:
    pct     = score / 100
    circum  = 2 * 3.14159 * 22
    offset  = circum * (1 - pct)
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 50 50">
        <circle cx="25" cy="25" r="22" fill="none" stroke="#1a2640" stroke-width="4"/>
        <circle cx="25" cy="25" r="22" fill="none" stroke="{color}" stroke-width="4"
            stroke-dasharray="{circum:.1f}" stroke-dashoffset="{offset:.1f}"
            stroke-linecap="round" transform="rotate(-90 25 25)"/>
        <text x="25" y="30" text-anchor="middle" fill="{color}"
            font-size="12" font-weight="800" font-family="Syne,sans-serif">{score}</text>
    </svg>"""

def header_html(title: str, subtitle: str = "") -> str:
    return f"""
    <div style="margin-bottom:24px">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
            <div style="width:3px;height:28px;background:linear-gradient(180deg,#3b82f6,#06b6d4);
                border-radius:2px"></div>
            <h2 style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;
                color:#e2e8f0;margin:0;letter-spacing:-0.5px">{title}</h2>
        </div>
        {f'<p style="color:#4b6278;font-size:11px;margin:0 0 0 15px">{subtitle}</p>' if subtitle else ''}
    </div>"""

# ──────────────────────────────────────────
# VIEW 1: COMMAND CENTER (Landing)
# ──────────────────────────────────────────
def render_command_center(all_team_data: list):
    # ── MASTHEAD ──
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a0f1e 0%,#0d1628 50%,#091020 100%);
         border:1px solid #1a2640;border-radius:12px;padding:28px 36px;margin-bottom:24px;
         position:relative;overflow:hidden">
        <div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;
             background:radial-gradient(circle,rgba(59,130,246,0.08) 0%,transparent 70%);
             border-radius:50%"></div>
        <div style="position:absolute;bottom:-30px;left:30%;width:150px;height:150px;
             background:radial-gradient(circle,rgba(6,182,212,0.06) 0%,transparent 70%);
             border-radius:50%"></div>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;position:relative">
            <div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                     color:#3b82f6;letter-spacing:3px;margin-bottom:6px">PI SPRINT COMMAND CENTER</div>
                <h1 style="font-family:'Syne',sans-serif;font-size:32px;font-weight:800;
                     color:#f1f5f9;margin:0 0 4px 0;letter-spacing:-1px">Sprint Visibility</h1>
                <p style="color:#4b6278;font-size:12px;margin:0">
                    5 Scrum Teams &nbsp;·&nbsp; HRM Project &nbsp;·&nbsp; 
                    Live as of {}</p>
            </div>
            <div style="text-align:right">
                <div style="font-size:10px;color:#4b6278;margin-bottom:4px">OVERALL PI HEALTH</div>
                <div style="font-family:'Syne',sans-serif;font-size:36px;font-weight:800;
                     color:#3b82f6">{}</div>
            </div>
        </div>
    </div>
    """.format(
        datetime.now().strftime("%d %b %Y %H:%M"),
        _overall_health_label(all_team_data)
    ), unsafe_allow_html=True)

    # ── CROSS-TEAM KPI ROW ──
    kpis = _compute_kpis(all_team_data)
    k1, k2, k3, k4, k5 = st.columns(5)
    for col, (label, val, sub, color) in zip(
        [k1, k2, k3, k4, k5],
        [
            ("Total Items",       kpis["total"],      "across 5 teams",            "#3b82f6"),
            ("Completed",         kpis["done"],        f"{kpis['done_pct']}% done", "#10b981"),
            ("🔴 High Spill Risk", kpis["high"],       "items at high risk",         "#ef4444"),
            ("🟡 On Watch",        kpis["watch"],      "items to monitor",           "#f59e0b"),
            ("🔥 Overburns",       kpis["overburns"],  "exceeding estimate",         "#f97316"),
        ]
    ):
        col.markdown(f"""
        <div style="background:#0d1424;border:1px solid #1a2640;border-top:2px solid {color};
             border-radius:8px;padding:16px;text-align:center">
            <div style="font-size:10px;color:#4b6278;letter-spacing:1px;margin-bottom:6px">{label}</div>
            <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:{color}">{val}</div>
            <div style="font-size:10px;color:#374151;margin-top:4px">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── TEAM CARDS ──
    st.markdown(header_html(
        "Team Sprint Health",
        "Ranked by spill risk — click a team to drill into their sprint detail"
    ), unsafe_allow_html=True)

    # Sort: critical → atrisk → watch → healthy → no_data
    order = {"critical": 0, "atrisk": 1, "watch": 2, "healthy": 3, "no_data": 4}
    sorted_data = sorted(all_team_data,
                         key=lambda x: order.get(x.get("health", {}).get("status", "no_data"), 4))

    cols = st.columns(5)
    for col, tdata in zip(cols, sorted_data):
        with col:
            _render_team_card(tdata)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── FEATURE RISK TABLE ──
    st.markdown(header_html(
        "Feature Risk Across PI",
        "Features impacted by delayed or overburning tasks — PI delivery at risk"
    ), unsafe_allow_html=True)
    _render_feature_risk_table(all_team_data)


def _render_team_card(tdata: dict):
    team      = tdata.get("team", "")
    health    = tdata.get("health", {})
    status    = health.get("status", "no_data")
    cfg       = STATUS_CONFIG[status]
    avatar    = TEAM_AVATARS.get(team, "🔷")
    score     = health.get("score", 0)
    sprint    = tdata.get("sprint_name", "—")
    error     = tdata.get("error")
    bar_color = cfg["color"]
    comp_pct  = health.get("completion_pct", 0)
    bar_fill  = min(comp_pct, 100)

    if error:
        body_html = f'<div style="font-size:10px;color:#ef4444;margin-top:8px">{error}</div>'
    else:
        body_html = (
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">'
            f'<div style="background:#080c14;border-radius:4px;padding:8px;text-align:center">'
            f'<div style="font-size:18px;font-weight:800;color:#ef4444">{health.get("high_count", 0)}</div>'
            f'<div style="font-size:9px;color:#4b6278">HIGH RISK</div></div>'
            f'<div style="background:#080c14;border-radius:4px;padding:8px;text-align:center">'
            f'<div style="font-size:18px;font-weight:800;color:#f59e0b">{health.get("watch_count", 0)}</div>'
            f'<div style="font-size:9px;color:#4b6278">WATCH</div></div>'
            f'<div style="background:#080c14;border-radius:4px;padding:8px;text-align:center">'
            f'<div style="font-size:18px;font-weight:800;color:#f97316">{health.get("overburn_count", 0)}</div>'
            f'<div style="font-size:9px;color:#4b6278">OVERBURN</div></div>'
            f'<div style="background:#080c14;border-radius:4px;padding:8px;text-align:center">'
            f'<div style="font-size:18px;font-weight:800;color:#10b981">{health.get("completion_pct", 0)}%</div>'
            f'<div style="font-size:9px;color:#4b6278">COMPLETE</div></div>'
            f'</div>'
            f'<div style="font-size:9px;color:#4b6278;margin-bottom:2px">SPRINT COMPLETION</div>'
            f'<div style="background:#1a2640;border-radius:3px;height:6px;overflow:hidden;margin-top:4px">'
            f'<div style="width:{bar_fill}%;height:100%;background:{bar_color};border-radius:3px"></div></div>'
        )

    circum = 138.2
    offset = circum * (1 - score / 100)
    ring_svg = (
        f'<svg width="50" height="50" viewBox="0 0 50 50">'
        f'<circle cx="25" cy="25" r="22" fill="none" stroke="#1a2640" stroke-width="4"/>'
        f'<circle cx="25" cy="25" r="22" fill="none" stroke="{bar_color}" stroke-width="4"'
        f' stroke-dasharray="{circum}" stroke-dashoffset="{offset:.1f}"'
        f' stroke-linecap="round" transform="rotate(-90 25 25)"/>'
        f'<text x="25" y="30" text-anchor="middle" fill="{bar_color}"'
        f' font-size="12" font-weight="800">{score}</text>'
        f'</svg>'
    )

    badge_cfg = STATUS_CONFIG.get(status, STATUS_CONFIG["no_data"])
    badge = (
        f'<span style="background:{badge_cfg["bg"]};color:{badge_cfg["color"]};'
        f'border:1px solid {badge_cfg["border"]};border-radius:3px;padding:2px 8px;'
        f'font-size:10px;font-weight:700;letter-spacing:1px">'
        f'{badge_cfg["icon"]} {badge_cfg["label"]}</span>'
    )

    card_html = (
        f'<div style="background:#0d1424;border:2px solid {cfg["border"]};border-radius:10px;'
        f'padding:18px;position:relative;overflow:hidden;box-shadow:0 0 20px {cfg["color"]}18">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:3px;'
        f'background:linear-gradient(90deg,{cfg["color"]},transparent)"></div>'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">'
        f'<div>'
        f'<div style="font-size:22px;margin-bottom:4px">{avatar}</div>'
        f'<div style="font-size:13px;font-weight:800;color:#e2e8f0;line-height:1.2">{team}</div>'
        f'<div style="font-size:9px;color:#374151;margin-top:2px">{sprint}</div>'
        f'</div>'
        f'<div>{ring_svg}</div>'
        f'</div>'
        f'<div style="margin-bottom:10px">{badge}</div>'
        f'{body_html}'
        f'</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)

    if st.button(f"View {team.split()[0]} →", key=f"btn_{team}", use_container_width=True):
        st.session_state["view"]          = "team_detail"
        st.session_state["selected_team"] = team
        st.rerun()




def _render_feature_risk_table(all_team_data: list):
    rows = []
    for tdata in all_team_data:
        team  = tdata.get("team", "")
        items = tdata.get("items", [])
        for item in items:
            if item.get("spill_risk") in ["high", "watch"] or item.get("is_overburn"):
                feature = item.get("feature")
                backlog = item.get("backlog_item")
                rows.append({
                    "Team":           team,
                    "Feature":        feature["title"][:50] + "…" if feature and len(feature.get("title",""))>50 else (feature["title"] if feature else "—"),
                    "Backlog Item":   backlog["title"][:45] + "…" if backlog and len(backlog.get("title",""))>45 else (backlog["title"] if backlog else "—"),
                    "At-Risk Task":   item["title"][:45] + "…" if len(item["title"])>45 else item["title"],
                    "Assignee":       item["assignee"].split(" ")[0] if item["assignee"] else "—",
                    "Risk":           item["spill_risk"].upper() if item["spill_risk"] != "none" else "—",
                    "Overburn":       f"+{item['overrun_hours']:.1f}h" if item["is_overburn"] else "—",
                    "State":          item["state"],
                })

    if not rows:
        st.markdown("""<div style="background:#0d1424;border:1px solid #1a2640;border-radius:8px;
            padding:24px;text-align:center;color:#374151;font-size:12px">
            No features at risk — sprint looking healthy! 🎉</div>""", unsafe_allow_html=True)
        return

    df = pd.DataFrame(rows)

    def color_risk(val):
        if val == "HIGH":   return "color: #ef4444; font-weight: bold"
        if val == "WATCH":  return "color: #f59e0b; font-weight: bold"
        return "color: #4b6278"

    def color_overburn(val):
        return "color: #f97316; font-weight: bold" if val != "—" else "color: #374151"

    styled = (df.style
              .applymap(color_risk,     subset=["Risk"])
              .applymap(color_overburn, subset=["Overburn"])
              .set_properties(**{
                  "background-color": "#0d1424",
                  "color": "#94a3b8",
                  "border": "1px solid #1a2640",
                  "font-size": "11px",
                  "font-family": "JetBrains Mono, monospace",
              })
              .set_table_styles([{
                  "selector": "th",
                  "props": [
                      ("background-color", "#080c14"),
                      ("color", "#4b6278"),
                      ("font-size", "10px"),
                      ("letter-spacing", "1px"),
                      ("text-transform", "uppercase"),
                      ("border", "1px solid #1a2640"),
                  ]
              }]))

    st.dataframe(df, use_container_width=True, hide_index=True, height=320)


def _overall_health_label(all_team_data: list) -> str:
    statuses = [t.get("health", {}).get("status", "no_data") for t in all_team_data]
    if "critical" in statuses: return "🔴 CRITICAL"
    if "atrisk"   in statuses: return "🟠 AT RISK"
    if "watch"    in statuses: return "🟡 WATCH"
    return "🟢 HEALTHY"


def _compute_kpis(all_team_data: list) -> dict:
    all_items = [item for t in all_team_data for item in t.get("items", [])]
    total     = len(all_items)
    done      = sum(1 for i in all_items if i["state"] in COMPLETED_STATES)
    return {
        "total":    total,
        "done":     done,
        "done_pct": round(done/total*100) if total else 0,
        "high":     sum(1 for i in all_items if i.get("spill_risk") == "high"),
        "watch":    sum(1 for i in all_items if i.get("spill_risk") == "watch"),
        "overburns":sum(1 for i in all_items if i.get("is_overburn")),
    }

# ──────────────────────────────────────────
# VIEW 2: TEAM SPRINT DETAIL
# ──────────────────────────────────────────
def render_team_detail(tdata: dict):
    team   = tdata.get("team", "")
    health = tdata.get("health", {})
    items  = tdata.get("items", [])
    avatar = TEAM_AVATARS.get(team, "🔷")
    cfg    = STATUS_CONFIG.get(health.get("status","no_data"), STATUS_CONFIG["no_data"])

    # ── BACK BUTTON + HEADER ──
    col_back, col_title = st.columns([1, 8])
    with col_back:
        if st.button("← Back", key="back_btn"):
            st.session_state["view"] = "command_center"
            st.rerun()
    with col_title:
        sprint_end   = tdata.get("sprint_end")
        sprint_start = tdata.get("sprint_start")
        date_str     = ""
        if sprint_start and sprint_end:
            date_str = f"{sprint_start.strftime('%b %d')} – {sprint_end.strftime('%b %d, %Y')}"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px">
            <span style="font-size:24px">{avatar}</span>
            <div>
                <h2 style="font-family:'Syne',sans-serif;font-size:20px;font-weight:800;
                    color:#e2e8f0;margin:0">{team}</h2>
                <div style="font-size:11px;color:#4b6278">{tdata.get('sprint_name','—')} &nbsp;·&nbsp; {date_str}</div>
            </div>
            <div style="margin-left:12px">{status_badge_html(health.get('status','no_data'))}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── KPI ROW ──
    total_est  = sum(i.get("original_estimate", 0) or 0 for i in items)
    total_done = sum(i.get("completed_work", 0)    or 0 for i in items)
    total_rem  = sum(i.get("remaining_work", 0)     or 0 for i in items)
    done_items = [i for i in items if i["state"] in COMPLETED_STATES]
    high_items = [i for i in items if i.get("spill_risk") == "high"]
    over_items = [i for i in items if i.get("is_overburn")]

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    for col, (label, val, color) in zip(
        [k1,k2,k3,k4,k5,k6],
        [
            ("Total Items",    len(items),         "#3b82f6"),
            ("Completed",      len(done_items),     "#10b981"),
            ("High Spill Risk",len(high_items),     "#ef4444"),
            ("Overburns",      len(over_items),     "#f97316"),
            ("Hours Logged",   f"{total_done:.0f}h","#06b6d4"),
            ("Hours Remaining",f"{total_rem:.0f}h", "#f59e0b"),
        ]
    ):
        col.markdown(f"""
        <div style="background:#0d1424;border:1px solid #1a2640;border-top:2px solid {color};
             border-radius:8px;padding:14px;text-align:center">
            <div style="font-size:9px;color:#4b6278;letter-spacing:1px">{label}</div>
            <div style="font-family:'Syne',sans-serif;font-size:24px;font-weight:800;color:{color};margin-top:4px">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── TWO PANELS: SPILL + OVERBURN ──
    col_spill, col_over = st.columns(2)

    with col_spill:
        spill_items = [i for i in items if i.get("spill_risk") in ["high","watch"]]
        spill_items.sort(key=lambda x: 0 if x["spill_risk"]=="high" else 1)
        st.markdown(f"""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
            color:#e2e8f0;margin-bottom:12px">⚠️ Potential Spillover
            <span style="background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3);
                border-radius:3px;padding:1px 8px;font-size:10px;margin-left:8px">{len(spill_items)}</span>
            </div>""", unsafe_allow_html=True)

        if spill_items:
            for item in spill_items:
                is_high  = item["spill_risk"] == "high"
                border_c = "#ef4444" if is_high else "#f59e0b"
                reasons  = "<br>".join(item.get("spill_reasons", []))
                st.markdown(f"""
                <div style="background:#080c14;border-left:3px solid {border_c};
                     border:1px solid #1a2640;border-left:3px solid {border_c};
                     border-radius:6px;padding:10px 12px;margin-bottom:8px">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start">
                        <div style="font-size:11px;color:#cbd5e1;flex:1;margin-right:8px">{item['title'][:60]}{'…' if len(item['title'])>60 else ''}</div>
                        {status_badge_html(item['spill_risk'], 9)}
                    </div>
                    <div style="font-size:10px;color:#4b6278;margin-top:4px">
                        {item['assignee'].split()[0] if item['assignee'] else '—'} &nbsp;·&nbsp; 
                        {item['state']} &nbsp;·&nbsp; {item.get('remaining_work',0)}h rem
                    </div>
                    <div style="font-size:9px;color:#374151;margin-top:4px">{reasons}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""<div style="background:#080c14;border:1px solid #1a2640;border-radius:6px;
                padding:20px;text-align:center;color:#374151;font-size:11px">
                No spillover risks detected 🎉</div>""", unsafe_allow_html=True)

    with col_over:
        over_items_sorted = sorted(over_items, key=lambda x: x.get("overrun_hours",0), reverse=True)
        st.markdown(f"""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
            color:#e2e8f0;margin-bottom:12px">🔥 Overburn Items
            <span style="background:rgba(249,115,22,0.15);color:#f97316;border:1px solid rgba(249,115,22,0.3);
                border-radius:3px;padding:1px 8px;font-size:10px;margin-left:8px">{len(over_items_sorted)}</span>
            </div>""", unsafe_allow_html=True)

        if over_items_sorted:
            for item in over_items_sorted:
                est       = item.get("original_estimate", 0) or 0
                done_h    = item.get("completed_work", 0) or 0
                rem_h     = item.get("remaining_work", 0) or 0
                overrun   = item.get("overrun_hours", 0)
                is_ip     = item["state"] in INPROGRESS_STATES
                effective = done_h + rem_h if is_ip else done_h
                burn_pct  = int((effective / est * 100)) if est > 0 else 0
                bar_color = "#ef4444" if burn_pct >= 150 else "#f97316"

                st.markdown(f"""
                <div style="background:#080c14;border:1px solid #1a2640;border-left:3px solid #f97316;
                     border-radius:6px;padding:10px 12px;margin-bottom:8px">
                    <div style="font-size:11px;color:#cbd5e1;margin-bottom:4px">
                        {item['title'][:60]}{'…' if len(item['title'])>60 else ''}</div>
                    <div style="font-size:10px;color:#4b6278">
                        {item['assignee'].split()[0] if item['assignee'] else '—'} &nbsp;·&nbsp;
                        Est: {est}h &nbsp;·&nbsp; 
                        {'Proj:' if is_ip else 'Actual:'} {effective:.1f}h &nbsp;·&nbsp;
                        <span style="color:#f97316;font-weight:bold">+{overrun:.1f}h over</span>
                    </div>
                    <div style="background:#1a2640;border-radius:2px;height:4px;margin-top:8px;overflow:hidden">
                        <div style="width:{min(burn_pct,100)}%;height:100%;background:{bar_color};border-radius:2px"></div>
                    </div>
                    <div style="font-size:9px;color:{bar_color};margin-top:2px">{burn_pct}% of estimate</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""<div style="background:#080c14;border:1px solid #1a2640;border-radius:6px;
                padding:20px;text-align:center;color:#374151;font-size:11px">
                No overburn items 🎉</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── MEMBER LOAD ──
    st.markdown(header_html("Team Member Load"), unsafe_allow_html=True)
    members = {}
    for item in items:
        a = item.get("assignee","Unassigned")
        if a not in members:
            members[a] = {"items":[],"done":0,"high":0,"over":0,"logged":0}
        members[a]["items"].append(item)
        if item["state"] in COMPLETED_STATES:
            members[a]["done"] += 1
        if item.get("spill_risk") == "high":
            members[a]["high"] += 1
        if item.get("is_overburn"):
            members[a]["over"] += 1
        members[a]["logged"] += item.get("completed_work",0) or 0

    member_cols = st.columns(min(len(members), 4))
    for i, (name, data) in enumerate(members.items()):
        col  = member_cols[i % 4]
        tot  = len(data["items"])
        pct  = int(data["done"]/tot*100) if tot else 0
        bc   = "#10b981" if pct>=80 else "#f59e0b" if pct>=50 else "#ef4444"
        init = "".join([p[0] for p in name.split()[:2]]).upper()
        with col:
            st.markdown(f"""
            <div style="background:#0d1424;border:1px solid #1a2640;border-radius:8px;padding:14px;margin-bottom:12px">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
                    <div style="width:28px;height:28px;border-radius:50%;background:#1a2640;
                         display:flex;align-items:center;justify-content:center;
                         font-size:10px;font-weight:700;color:#3b82f6">{init}</div>
                    <div>
                        <div style="font-size:11px;font-weight:700;color:#e2e8f0">{name.split()[0]}</div>
                        <div style="font-size:9px;color:#374151">{tot} items</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:8px">
                    <div style="text-align:center">
                        <div style="font-size:14px;font-weight:800;color:#10b981">{data['done']}</div>
                        <div style="font-size:8px;color:#374151">DONE</div>
                    </div>
                    <div style="text-align:center">
                        <div style="font-size:14px;font-weight:800;color:#ef4444">{data['high']}</div>
                        <div style="font-size:8px;color:#374151">HIGH</div>
                    </div>
                    <div style="font-size:14px;font-weight:800;color:#f97316;text-align:center">
                        <div>{data['over']}</div>
                        <div style="font-size:8px;color:#374151">OVER</div>
                    </div>
                </div>
                {mini_bar_html(pct, bc, 5)}
                <div style="font-size:9px;color:#374151;margin-top:3px">{pct}% complete · {data['logged']:.0f}h logged</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── ALL ITEMS TABLE ──
    st.markdown(header_html("All Sprint Items"), unsafe_allow_html=True)
    tab_all, tab_risk, tab_todo, tab_ip, tab_done = st.tabs([
        f"All ({len(items)})",
        f"⚠ At Risk ({sum(1 for i in items if i.get('spill_risk') in ['high','watch'] or i.get('is_overburn'))})",
        f"To Do ({sum(1 for i in items if i['state']=='To Do')})",
        f"In Progress ({sum(1 for i in items if i['state'] in INPROGRESS_STATES)})",
        f"Done ({len(done_items)})",
    ])

    def items_to_df(subset):
        return pd.DataFrame([{
            "ID":        i["id"],
            "Title":     i["title"][:50] + "…" if len(i["title"])>50 else i["title"],
            "Assignee":  i["assignee"].split()[0] if i["assignee"] else "—",
            "State":     i["state"],
            "Est(h)":    i.get("original_estimate") or "—",
            "Done(h)":   i.get("completed_work") or "—",
            "Rem(h)":    i.get("remaining_work") or "—",
            "Spill Risk":i.get("spill_risk","none").upper(),
            "Overburn":  f"+{i['overrun_hours']:.1f}h" if i.get("is_overburn") else "—",
            "Feature":   i["feature"]["title"][:30]+"…" if i.get("feature") and len(i["feature"]["title"])>30 else (i["feature"]["title"] if i.get("feature") else "—"),
        } for i in subset])

    for tab, subset in [
        (tab_all,  items),
        (tab_risk, [i for i in items if i.get("spill_risk") in ["high","watch"] or i.get("is_overburn")]),
        (tab_todo, [i for i in items if i["state"]=="To Do"]),
        (tab_ip,   [i for i in items if i["state"] in INPROGRESS_STATES]),
        (tab_done, done_items),
    ]:
        with tab:
            if subset:
                st.dataframe(items_to_df(subset), use_container_width=True, hide_index=True)
            else:
                st.info("No items in this category.")

    # Feature drill-down button
    at_risk_with_features = [i for i in items if (i.get("spill_risk") in ["high","watch"] or i.get("is_overburn")) and i.get("feature")]
    if at_risk_with_features:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("🔍 View Feature Risk Drill-Down →", key="feat_drill"):
            st.session_state["view"]         = "feature_risk"
            st.session_state["selected_team"] = tdata["team"]
            st.rerun()

# ──────────────────────────────────────────
# VIEW 3: FEATURE RISK DRILL-DOWN
# ──────────────────────────────────────────
def render_feature_risk(tdata: dict):
    team   = tdata.get("team","")
    items  = tdata.get("items", [])
    avatar = TEAM_AVATARS.get(team, "🔷")

    col_back, col_title = st.columns([1, 8])
    with col_back:
        if st.button("← Back", key="back_feat"):
            st.session_state["view"] = "team_detail"
            st.rerun()
    with col_title:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:20px">{avatar}</span>
            <h2 style="font-family:'Syne',sans-serif;font-size:20px;font-weight:800;
                color:#e2e8f0;margin:0">{team} · Feature Risk</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # Group at-risk items by Feature
    feature_groups = defaultdict(list)
    no_feature     = []

    for item in items:
        if item.get("spill_risk") in ["high","watch"] or item.get("is_overburn"):
            feat = item.get("feature")
            if feat:
                feature_groups[feat["id"]].append((feat, item))
            else:
                no_feature.append(item)

    if not feature_groups and not no_feature:
        st.success("No features at risk — all sprint items are on track! 🎉")
        return

    st.markdown(f"""<div style="font-size:12px;color:#4b6278;margin-bottom:20px">
        {len(feature_groups)} feature(s) impacted by delayed or overburning tasks</div>""",
        unsafe_allow_html=True)

    for fid, entries in feature_groups.items():
        feat   = entries[0][0]
        f_items = [e[1] for e in entries]
        high_c  = sum(1 for i in f_items if i.get("spill_risk")=="high")
        over_c  = sum(1 for i in f_items if i.get("is_overburn"))

        f_status = "critical" if high_c >= 2 else "atrisk" if high_c >= 1 else "watch"
        f_cfg    = STATUS_CONFIG[f_status]

        with st.expander(
            f"{f_cfg['icon']} Feature: {feat['title'][:70]} — {len(f_items)} at-risk task(s)",
            expanded=(f_status in ["critical","atrisk"])
        ):
            st.markdown(f"""
            <div style="display:flex;gap:16px;margin-bottom:14px">
                <div style="background:#080c14;border:1px solid #1a2640;border-radius:6px;padding:10px 16px">
                    <div style="font-size:9px;color:#4b6278">FEATURE ID</div>
                    <div style="font-size:13px;color:#3b82f6;font-weight:700">#{fid}</div>
                </div>
                <div style="background:#080c14;border:1px solid #1a2640;border-radius:6px;padding:10px 16px">
                    <div style="font-size:9px;color:#4b6278">PI DELIVERY RISK</div>
                    <div style="margin-top:2px">{status_badge_html(f_status)}</div>
                </div>
                <div style="background:#080c14;border:1px solid #1a2640;border-radius:6px;padding:10px 16px">
                    <div style="font-size:9px;color:#4b6278">IMPACTED TASKS</div>
                    <div style="font-size:13px;color:#f97316;font-weight:700">{len(f_items)}</div>
                </div>
                <div style="background:#080c14;border:1px solid #1a2640;border-radius:6px;padding:10px 16px">
                    <div style="font-size:9px;color:#4b6278">HIGH RISK TASKS</div>
                    <div style="font-size:13px;color:#ef4444;font-weight:700">{high_c}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Backlog items grouped
            backlog_groups = defaultdict(list)
            for item in f_items:
                bl = item.get("backlog_item")
                key = bl["id"] if bl else "no_backlog"
                backlog_groups[key].append((bl, item))

            for bl_key, bl_entries in backlog_groups.items():
                bl     = bl_entries[0][0]
                bl_lbl = bl["title"][:60] if bl else "No Backlog Item"
                st.markdown(f"""<div style="font-size:11px;color:#64748b;
                    border-left:2px solid #1a2640;padding-left:8px;margin:10px 0 6px 0">
                    📋 {bl_lbl}</div>""", unsafe_allow_html=True)

                for _, task in bl_entries:
                    is_high  = task.get("spill_risk") == "high"
                    border_c = "#ef4444" if is_high else ("#f97316" if task.get("is_overburn") else "#f59e0b")
                    reasons  = " · ".join(task.get("spill_reasons", []))
                    st.markdown(f"""
                    <div style="background:#080c14;border:1px solid #1a2640;
                         border-left:3px solid {border_c};border-radius:6px;
                         padding:10px 14px;margin:4px 0 4px 16px">
                        <div style="display:flex;justify-content:space-between">
                            <div style="font-size:11px;color:#cbd5e1">
                                #{task['id']} · {task['title'][:55]}{'…' if len(task['title'])>55 else ''}</div>
                            <div style="display:flex;gap:6px">
                                {status_badge_html(task['spill_risk'], 9) if task.get('spill_risk') != 'none' else ''}
                                {'<span style="background:rgba(249,115,22,0.15);color:#f97316;border:1px solid rgba(249,115,22,0.3);border-radius:3px;padding:1px 6px;font-size:9px">OVERBURN</span>' if task.get('is_overburn') else ''}
                            </div>
                        </div>
                        <div style="font-size:10px;color:#374151;margin-top:4px">
                            {task['assignee'].split()[0] if task['assignee'] else '—'} &nbsp;·&nbsp;
                            {task['state']} &nbsp;·&nbsp;
                            Rem: {task.get('remaining_work',0)}h
                            {f"&nbsp;·&nbsp; <span style='color:#f97316'>+{task['overrun_hours']:.1f}h over</span>" if task.get('is_overburn') else ''}
                        </div>
                        {f'<div style="font-size:9px;color:#4b6278;margin-top:3px">{reasons}</div>' if reasons else ''}
                    </div>
                    """, unsafe_allow_html=True)

# ──────────────────────────────────────────
# SIDEBAR: CONNECTION SETTINGS
# ──────────────────────────────────────────
def render_sidebar() -> dict | None:
    with st.sidebar:
        st.markdown("""
        <div style="font-family:'Syne',sans-serif;font-size:16px;font-weight:800;
             color:#e2e8f0;margin-bottom:16px">⚙️ Connection</div>
        """, unsafe_allow_html=True)

        org_url = st.text_input(
            "Azure DevOps Org URL",
            value=st.session_state.get("org_url", "https://dev.azure.com/YOUR_ORG"),
            placeholder="https://dev.azure.com/yourorg"
        )
        project = st.text_input(
            "Project Name",
            value=st.session_state.get("project", "YOUR_PROJECT"),
            placeholder="MyProject"
        )
        pat = st.text_input(
            "Personal Access Token (PAT)",
            value=st.session_state.get("pat", ""),
            type="password",
            placeholder="Paste your PAT here"
        )

        st.markdown("---")

        load_clicked = st.button("🔄 Load Live Data", use_container_width=True)
        demo_clicked = st.button("🧪 Use Demo Data",  use_container_width=True)

        if load_clicked and org_url and project and pat:
            st.session_state["org_url"] = org_url
            st.session_state["project"] = project
            st.session_state["pat"]     = pat
            st.session_state["use_demo"]= False
            st.session_state["loaded"]  = False
            st.rerun()

        if demo_clicked:
            st.session_state["use_demo"] = True
            st.session_state["loaded"]   = False
            st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style="font-size:10px;color:#374151;line-height:1.7">
            <b style="color:#4b6278">PAT Permissions needed:</b><br>
            · Work Items — Read<br>
            · Project & Team — Read<br><br>
            <b style="color:#4b6278">Data refreshes every 5 min</b><br>
            <a href="https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate"
               style="color:#3b82f6;font-size:10px">How to create a PAT →</a>
        </div>
        """, unsafe_allow_html=True)

    return {"org_url": org_url, "project": project, "pat": pat}

# ──────────────────────────────────────────
# DEMO DATA GENERATOR
# ──────────────────────────────────────────
def generate_demo_data() -> list:
    """Generate realistic demo data for all 5 teams."""
    from random import seed, randint, choice, random
    seed(42)
    today = date.today()

    demo_configs = {
        "Echo Engineers":   {"high":4, "watch":3, "overburn":5, "done_pct":0.45},
        "Code Commanders":  {"high":1, "watch":2, "overburn":2, "done_pct":0.60},
        "Beta Brigade":     {"high":3, "watch":2, "overburn":4, "done_pct":0.40},
        "Gamma Guardians":  {"high":0, "watch":1, "overburn":1, "done_pct":0.75},
        "Hyper Hackers":    {"high":0, "watch":0, "overburn":0, "done_pct":0.85},
    }

    features = [
        {"id": 1001, "title": "Employee Information Module v2.0", "type": "Feature", "state": "Active"},
        {"id": 1002, "title": "Payroll Processing Engine",        "type": "Feature", "state": "Active"},
        {"id": 1003, "title": "Leave Management System",          "type": "Feature", "state": "Active"},
        {"id": 1004, "title": "Performance Review Portal",        "type": "Feature", "state": "Active"},
        {"id": 1005, "title": "Recruitment & Onboarding Flow",    "type": "Feature", "state": "Active"},
    ]

    all_data = []
    item_id  = 130000

    for team_idx, (team, cfg) in enumerate(demo_configs.items()):
        sprint_start = date(2026, 5, 4)
        sprint_end   = date(2026, 5, 15)
        hrs_left     = calculate_working_hours_left(sprint_end)
        items        = []
        n_total      = randint(20, 35)

        for j in range(n_total):
            item_id += 1
            feat    = features[j % len(features)]
            bl_id   = 120000 + (team_idx * 100) + (j // 3)

            # Determine state & hours
            is_high    = j < cfg["high"]
            is_watch   = cfg["high"] <= j < cfg["high"] + cfg["watch"]
            is_overburn= j < cfg["overburn"]
            rand_done  = random() < cfg["done_pct"]

            if rand_done:
                state = choice(["Done","Done","Done","Resolved","Dev Completed"])
            elif is_high:
                state = choice(["To Do","On hold","Scheduled"])
            elif is_watch:
                state = choice(["In Progress","To Do"])
            else:
                state = choice(["To Do","In Progress","Done"])

            est = round(randint(1,20) * 0.5, 1)

            if state in COMPLETED_STATES:
                done_h = est * 1.3 if is_overburn else est * round(0.8 + random()*0.3, 1)
                rem_h  = 0
            elif state == "In Progress":
                done_h = round(est * random() * 0.6, 1)
                rem_h  = round(est * 1.4 - done_h, 1) if is_overburn else round(est - done_h + random()*2, 1)
            else:
                done_h = 0
                rem_h  = est if not is_high else est + randint(5,15)

            risk, reasons = classify_item_risk({
                "state": state, "original_estimate": est,
                "completed_work": done_h, "remaining_work": rem_h,
                "target_date": None, "sprint_end": sprint_end
            }, hrs_left)

            is_over, overrun = classify_overburn({
                "state": state, "original_estimate": est,
                "completed_work": done_h, "remaining_work": rem_h
            })

            items.append({
                "id":               item_id,
                "title":            f"[{'DEV' if j%3==0 else 'QA' if j%3==1 else 'BA'}] Task {item_id} — {feat['title'][:30]}",
                "type":             "Task",
                "state":            state,
                "assignee":         f"Member {(j % 6) + 1}",
                "original_estimate":est,
                "completed_work":   round(done_h, 1),
                "remaining_work":   round(rem_h, 1),
                "priority":         randint(1,4),
                "tags":             "26R1",
                "activity":         choice(["Development","Testing","Documentation"]),
                "start_date":       sprint_start.isoformat(),
                "target_date":      sprint_end.isoformat(),
                "parent_id":        bl_id,
                "sprint_name":      "26R1_SP06",
                "sprint_start":     sprint_start,
                "sprint_end":       sprint_end,
                "team":             team,
                "url":              "#",
                "spill_risk":       risk,
                "spill_reasons":    reasons,
                "is_overburn":      is_over,
                "overrun_hours":    overrun,
                "backlog_item":     {"id": bl_id, "title": f"Backlog: {feat['title'][:40]}", "type": "Product Backlog Item", "state": "Active"},
                "feature":          feat,
            })

        health = score_team_health(items)
        all_data.append({
            "team":         team,
            "sprint_name":  "26R1_SP06",
            "sprint_start": sprint_start,
            "sprint_end":   sprint_end,
            "hrs_left":     hrs_left,
            "items":        items,
            "health":       health,
        })

    return all_data

# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────
def main():
    # Init session state
    if "view"          not in st.session_state: st.session_state["view"]          = "command_center"
    if "selected_team" not in st.session_state: st.session_state["selected_team"] = TEAMS[0]
    if "use_demo"      not in st.session_state: st.session_state["use_demo"]      = True
    if "loaded"        not in st.session_state: st.session_state["loaded"]        = False
    if "all_data"      not in st.session_state: st.session_state["all_data"]      = []

    conn = render_sidebar()

    # ── LOAD DATA ──
    if not st.session_state["loaded"]:
        if st.session_state.get("use_demo"):
            with st.spinner("Loading demo data…"):
                st.session_state["all_data"] = generate_demo_data()
                st.session_state["loaded"]   = True
        elif st.session_state.get("pat"):
            with st.spinner("Connecting to Azure DevOps…"):
                all_data = []
                prog     = st.progress(0)
                for i, team in enumerate(TEAMS):
                    tdata = load_team_data(
                        st.session_state["org_url"],
                        st.session_state["project"],
                        st.session_state["pat"],
                        team
                    )
                    all_data.append(tdata)
                    prog.progress((i+1)/len(TEAMS))
                st.session_state["all_data"] = all_data
                st.session_state["loaded"]   = True
        else:
            # Show welcome screen
            st.markdown("""
            <div style="display:flex;flex-direction:column;align-items:center;
                 justify-content:center;min-height:60vh;text-align:center">
                <div style="font-size:48px;margin-bottom:16px">🚀</div>
                <h1 style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;
                    color:#e2e8f0;margin-bottom:8px">PI Sprint Command Center</h1>
                <p style="color:#4b6278;font-size:13px;max-width:420px;line-height:1.6">
                    Connect your Azure DevOps account using the sidebar,<br>
                    or click <strong style="color:#3b82f6">Use Demo Data</strong> to explore the dashboard.
                </p>
            </div>
            """, unsafe_allow_html=True)
            return

    all_data = st.session_state["all_data"]

    # ── ROUTE VIEWS ──
    view = st.session_state["view"]

    if view == "command_center":
        render_command_center(all_data)

    elif view == "team_detail":
        selected = st.session_state.get("selected_team", TEAMS[0])
        tdata    = next((t for t in all_data if t["team"] == selected), None)
        if tdata:
            render_team_detail(tdata)
        else:
            st.error(f"No data for team: {selected}")
            st.session_state["view"] = "command_center"
            st.rerun()

    elif view == "feature_risk":
        selected = st.session_state.get("selected_team", TEAMS[0])
        tdata    = next((t for t in all_data if t["team"] == selected), None)
        if tdata:
            render_feature_risk(tdata)
        else:
            st.session_state["view"] = "command_center"
            st.rerun()


if __name__ == "__main__":
    main()
