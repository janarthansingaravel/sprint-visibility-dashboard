"""
HRM PI & Sprint Command Centre
PI Execution Centre + Sprint Monitor · Azure DevOps
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import base64
from collections import defaultdict
from io import BytesIO
import json
import re

st.set_page_config(
    page_title="HRM Command Centre",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────
# ACCESS CONTROL
# ─────────────────────────────────────────────────────────────────
def check_access():
    try:
        allowed = st.secrets["access"]["allowed_emails"]
        user_email = st.user.email if hasattr(st, "user") and st.user else None
        if not user_email:
            return True
        if user_email not in allowed:
            st.markdown(f"""
            <div style="display:flex;flex-direction:column;align-items:center;
                 justify-content:center;min-height:80vh;text-align:center">
                <div style="font-size:56px;margin-bottom:20px">🚫</div>
                <div style="font-size:22px;font-weight:700;color:#1a202c;margin-bottom:10px">Access Denied</div>
                <div style="font-size:14px;color:#6b7280;max-width:400px;line-height:1.7">
                    <b>{user_email}</b> is not authorised.<br>Contact the Scrum Master to request access.
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.stop()
    except Exception:
        pass
    return True

check_access()

# ─────────────────────────────────────────────────────────────────
# AUTO-LOAD SECRETS
# ─────────────────────────────────────────────────────────────────
def load_secrets():
    try:
        s = st.secrets["azure_devops"]
        if not st.session_state.get("pat"):
            st.session_state["org_url"]  = s.get("org_url", "")
            st.session_state["project"]  = s.get("project", "HRM")
            st.session_state["pat"]      = s.get("pat", "")
    except Exception:
        pass

load_secrets()

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────
TEAMS        = ["Echo Engineers", "Code Commanders", "Beta Brigade", "Gamma Guardians", "Hyper Hackers"]
TEAM_AVATARS = {"Echo Engineers": "⚡", "Code Commanders": "🛡️", "Beta Brigade": "🔥", "Gamma Guardians": "🌀", "Hyper Hackers": "💥"}
TEAM_COLORS  = {"Echo Engineers": "#2563eb", "Code Commanders": "#7c3aed", "Beta Brigade": "#ea580c", "Gamma Guardians": "#059669", "Hyper Hackers": "#db2777"}

COMPLETED   = ["Done", "Resolved", "Dev Completed"]
INPROGRESS  = ["In Progress", "Scheduled"]
VALID_TYPES = ["Task", "Bug"]

PROJECTS = ["HRM"]

PM_NAME = "Janarthan Singaravel"

# Sri Lanka Mercantile Holidays 2025–2026
LK_HOLIDAYS = {
    date(2025, 1, 13), date(2025, 1, 14), date(2025, 2, 4), date(2025, 2, 12),
    date(2025, 2, 26), date(2025, 3, 13), date(2025, 3, 31), date(2025, 4, 12),
    date(2025, 4, 13), date(2025, 4, 14), date(2025, 4, 15), date(2025, 4, 18),
    date(2025, 5, 1),  date(2025, 5, 12), date(2025, 5, 13), date(2025, 6, 7),
    date(2025, 6, 10), date(2025, 7, 10), date(2025, 8, 8),  date(2025, 9, 5),
    date(2025, 9, 7),  date(2025, 10, 6), date(2025, 11, 5), date(2025, 12, 4),
    date(2025, 12, 25),
    date(2026, 1, 3),  date(2026, 1, 15), date(2026, 2, 1),  date(2026, 2, 4),
    date(2026, 2, 15), date(2026, 3, 2),  date(2026, 3, 21), date(2026, 4, 1),
    date(2026, 4, 3),  date(2026, 4, 13), date(2026, 4, 14), date(2026, 5, 1),
    date(2026, 5, 2),  date(2026, 5, 28), date(2026, 5, 30), date(2026, 6, 29),
    date(2026, 7, 29), date(2026, 8, 26), date(2026, 8, 27), date(2026, 9, 26),
    date(2026, 10, 25),date(2026, 11, 8), date(2026, 11, 24),date(2026, 12, 23),
    date(2026, 12, 25),
}

# Feature status mapping for PI dashboard
PI_STATUS_MAP = {
    "On hold":                      "On Hold",
    "On Hold":                      "On Hold",
    "Feature Approval":             "Feature Approval",
    "PI Ready":                     "PI Ready",
    "Grooming Pending":             "Grooming",
    "Grooming Completed":           "Grooming",
    "Solutioning Pending":          "Solutioning",
    "Solutioning In-Progress":      "Solutioning",
    "Solutioning Completed":        "Solutioning",
    "Dev Pending":                  "Development",
    "Dev In Progress":              "Development",
    "Dev Completed":                "Development",
    "QA Pending":                   "Testing",
    "QA In Progress":               "Testing",
    "QA Completed":                 "Testing",
    "Release Materials Pending":    "Release Materials",
    "Release Materials In-Progress":"Release Materials",
    "Release Materials Completed":  "Release Materials",
    "PO Review":                    "PO Review",
    "Blocked by Dependent Bugs":    "Blocked by Dependent Bugs",
    "Release Ready":                "Release Ready",
    "Done":                         "Done",
}

PI_STATUS_COLORS = {
    "On Hold":                  {"bg": "#f5f3ff", "color": "#5b21b6", "border": "#ddd6fe"},
    "Feature Approval":         {"bg": "#eff6ff", "color": "#1d4ed8", "border": "#bfdbfe"},
    "PI Ready":                 {"bg": "#ecfdf5", "color": "#065f46", "border": "#a7f3d0"},
    "Grooming":                 {"bg": "#fef3c7", "color": "#92400e", "border": "#fde68a"},
    "Solutioning":              {"bg": "#fff7ed", "color": "#9a3412", "border": "#fed7aa"},
    "Development":              {"bg": "#eff6ff", "color": "#1e40af", "border": "#bfdbfe"},
    "Testing":                  {"bg": "#f0fdf4", "color": "#166534", "border": "#bbf7d0"},
    "Release Materials":        {"bg": "#fdf4ff", "color": "#7e22ce", "border": "#e9d5ff"},
    "PO Review":                {"bg": "#fff1f2", "color": "#9f1239", "border": "#fecdd3"},
    "Blocked by Dependent Bugs":{"bg": "#fef2f2", "color": "#991b1b", "border": "#fecaca"},
    "Release Ready":            {"bg": "#f0fdf4", "color": "#14532d", "border": "#86efac"},
    "Done":                     {"bg": "#f0fdf4", "color": "#15803d", "border": "#bbf7d0"},
}

STATUS = {
    "critical": {"color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca", "text": "Critical",  "icon": "🔴"},
    "atrisk":   {"color": "#d97706", "bg": "#fffbeb", "border": "#fde68a", "text": "At Risk",   "icon": "🟡"},
    "watch":    {"color": "#ca8a04", "bg": "#fefce8", "border": "#fef08a", "text": "Watch",     "icon": "🟡"},
    "healthy":  {"color": "#16a34a", "bg": "#f0fdf4", "border": "#bbf7d0", "text": "Healthy",   "icon": "🟢"},
    "no_data":  {"color": "#6b7280", "bg": "#f9fafb", "border": "#e5e7eb", "text": "No Data",   "icon": "⚫"},
}

BLOCKED_TAGS = {
    "Env-Unstable":    {"label": "Environment Unstable", "icon": "🌩️", "color": "#7c3aed", "owner": "DevOps Team",   "desc": "Env unstable"},
    "PR-Approval":     {"label": "PR Awaiting Approval", "icon": "🔀", "color": "#1d4ed8", "owner": "Tech Lead",     "desc": "PR waiting for review"},
    "Test-Data-Issue": {"label": "Test Data Issue",      "icon": "🗄️", "color": "#b45309", "owner": "BA / QA Lead", "desc": "Missing/incorrect test data"},
    "Blocked":         {"label": "Blocked",              "icon": "🚧", "color": "#dc2626", "owner": "Scrum Master",  "desc": "Needs escalation"},
}

# ─────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#f7f9fc!important;color:#1a202c!important;}
.stApp{background:#f7f9fc!important;}
.block-container{padding:0!important;max-width:100%!important;}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;display:none!important;}
[data-testid="stSidebar"]{background:#ffffff!important;border-right:1px solid #e8ecf0!important;}
[data-testid="stSidebar"] input{background:#f7f9fc!important;border:1px solid #e8ecf0!important;border-radius:6px!important;font-size:13px!important;}
[data-testid="stSidebar"] label{font-size:11px!important;font-weight:600!important;color:#8896a5!important;text-transform:uppercase!important;}
.stButton>button{font-family:'Inter',sans-serif!important;font-size:12px!important;font-weight:500!important;border-radius:6px!important;border:1px solid #d1d9e0!important;background:#ffffff!important;color:#374151!important;padding:5px 12px!important;transition:all 0.15s!important;}
.stButton>button:hover{border-color:#2563eb!important;color:#2563eb!important;background:#eff6ff!important;}
.stDownloadButton>button{font-size:12px!important;font-weight:500!important;border-radius:6px!important;background:#eff6ff!important;color:#2563eb!important;border:1px solid #bfdbfe!important;}
[data-testid="stMetric"]{background:#ffffff;border-radius:8px;padding:.8rem;border:1px solid #e8ecf0;}
[data-testid="stMetricValue"]{font-size:1.8rem!important;font-weight:700!important;}
[data-testid="stMetricLabel"]{font-size:12px!important;font-weight:600!important;color:#6b7280!important;}
.stDataFrame{border-radius:8px!important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:#f7f9fc;}
::-webkit-scrollbar-thumb{background:#d1d9e0;border-radius:2px;}
hr{border-color:#e8ecf0!important;margin:.6rem 0!important;}
div[data-testid="stTabs"] button{font-size:13px!important;font-weight:500!important;color:#6b7280!important;padding:10px 20px!important;}
div[data-testid="stTabs"] button[aria-selected="true"]{font-weight:700!important;color:#1a202c!important;}
div[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:0!important;border-bottom:2px solid #e8ecf0!important;background:#ffffff!important;padding:0 24px!important;}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"]{background:#2563eb!important;height:2px!important;}
.stChatMessage{background:#ffffff!important;border:1px solid #e8ecf0!important;border-radius:10px!important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# DATE / WORKING DAY HELPERS
# ─────────────────────────────────────────────────────────────────
def is_working_day(d: date) -> bool:
    return d.weekday() < 5 and d not in LK_HOLIDAYS

def working_days_between(start: date, end: date) -> int:
    if not start or not end or start > end:
        return 0
    count = 0
    cur = start
    while cur <= end:
        if is_working_day(cur):
            count += 1
        cur += timedelta(days=1)
    return count

def working_days_remaining(end: date) -> int:
    if not end:
        return 0
    today = date.today()
    if today > end:
        return 0
    return working_days_between(today, end)

def working_hours_remaining(end: date) -> int:
    return working_days_remaining(end) * 8

def pd_(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def inits(n):
    p = str(n).split()
    return "".join(x[0] for x in p[:2]).upper() if p else "?"

# ─────────────────────────────────────────────────────────────────
# AZURE DEVOPS CLIENT
# ─────────────────────────────────────────────────────────────────
class DevOpsClient:
    def __init__(self, org, pat):
        self.org = org.rstrip("/")
        tok = base64.b64encode(f":{pat}".encode()).decode()
        self.h = {"Authorization": f"Basic {tok}", "Content-Type": "application/json"}

    def _get(self, url, p=None):
        try:
            r = requests.get(url, headers=self.h, params=p, timeout=12)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def _post(self, url, b):
        try:
            r = requests.post(url, headers=self.h, json=b, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def _wiql(self, proj, query):
        url = f"{self.org}/{proj}/_apis/wit/wiql?api-version=7.0"
        try:
            r = requests.post(url, headers=self.h, json={"query": query}, timeout=15)
            if not r.ok:
                # Store error for debugging
                st.session_state["_wiql_last_error"] = f"{r.status_code}: {r.text[:300]}"
                return []
            d = r.json()
            if d.get("workItems"):
                return [w["id"] for w in d["workItems"]]
            # relations-based result
            if d.get("workItemRelations"):
                return [w["target"]["id"] for w in d["workItemRelations"] if w.get("target")]
            return []
        except Exception as e:
            st.session_state["_wiql_last_error"] = str(e)
            return []

    def get_sprint(self, proj, team):
        base = f"{self.org}/{proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations"
        d = self._get(base, {"$timeframe": "current", "api-version": "7.0"})
        if d and d.get("value"):
            sp = d["value"][0]; sp["_tf"] = "current"; return sp
        d = self._get(base, {"$timeframe": "past", "api-version": "7.0"})
        if d and d.get("value"):
            sp = sorted(d["value"], key=lambda x: x.get("attributes", {}).get("finishDate", ""), reverse=True)[0]
            sp["_tf"] = "past"; return sp
        return None

    def get_wi_ids_for_sprint(self, proj, team, iid):
        d = self._get(
            f"{self.org}/{proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations/{iid}/workitems",
            {"api-version": "7.0"}
        )
        if not d:
            return []
        return list(set(w["target"]["id"] for w in d.get("workItemRelations", []) if w.get("target") and w["target"].get("id")))

    def get_wi_batch(self, ids, fields=None):
        if not ids:
            return []
        if fields is None:
            fields = [
                "System.Id", "System.Title", "System.WorkItemType", "System.State",
                "System.AssignedTo", "System.Parent", "System.Tags", "System.TeamProject",
                "System.AreaPath", "System.IterationPath",
                "Microsoft.VSTS.Scheduling.OriginalEstimate",
                "Microsoft.VSTS.Scheduling.CompletedWork",
                "Microsoft.VSTS.Scheduling.RemainingWork",
                "Microsoft.VSTS.Common.Priority",
                "Microsoft.VSTS.Scheduling.StartDate",
                "Microsoft.VSTS.Scheduling.TargetDate",
                "System.Description", "System.CommentCount",
            ]
        out = []
        for i in range(0, len(ids), 200):
            batch = ids[i:i+200]
            try:
                r = requests.post(
                    f"{self.org}/_apis/wit/workitemsbatch?api-version=7.0",
                    headers=self.h,
                    json={"ids": batch, "fields": fields},
                    timeout=15
                )
                if r.ok:
                    out.extend(r.json().get("value", []))
                else:
                    # Store error and try with minimal fields as fallback
                    st.session_state["_wiql_last_error"] = f"batch {r.status_code}: {r.text[:200]}"
                    # Fallback: fetch with minimal safe fields
                    r2 = requests.post(
                        f"{self.org}/_apis/wit/workitemsbatch?api-version=7.0",
                        headers=self.h,
                        json={"ids": batch, "fields": [
                            "System.Id", "System.Title", "System.WorkItemType",
                            "System.State", "System.AssignedTo", "System.Tags",
                            "System.AreaPath", "Microsoft.VSTS.Common.Priority",
                            "Microsoft.VSTS.Scheduling.StartDate",
                            "Microsoft.VSTS.Scheduling.TargetDate",
                            "Custom.PI",
                            "Custom.ScrumTeamOwnership", "Custom.SolutionOwner",
                            "Custom.DependantScrumTeam",
                            "Custom.PlannedDevEffort", "Custom.PlannedQAEffort",
                        ]},
                        timeout=15
                    )
                    if r2.ok:
                        out.extend(r2.json().get("value", []))
            except Exception as e:
                st.session_state["_wiql_last_error"] = str(e)
        return out

    def get_comments(self, proj, wi_id):
        url = f"{self.org}/{proj}/_apis/wit/workItems/{wi_id}/comments?api-version=7.0-preview.3"
        d = self._get(url)
        if d:
            return d.get("comments", [])
        return []

    def get_pi_epics(self, proj, pi_name):
        """Get PI Epic by title — used only for start/end dates"""
        q = f"""SELECT [System.Id] FROM WorkItems
                WHERE [System.TeamProject] = '{proj}'
                AND [System.WorkItemType] = 'Epic'
                AND [System.Title] CONTAINS '{pi_name}'"""
        return self._wiql(proj, q)

    def get_features_for_pi(self, proj, pi_name):
        """Get all Features where Custom.PI = pi_name"""
        q = f"""SELECT [System.Id] FROM WorkItems
                WHERE [System.TeamProject] = '{proj}'
                AND [System.WorkItemType] = 'Feature'
                AND [Custom.PI] = '{pi_name}'"""
        ids = self._wiql(proj, q)
        if not ids:
            return []
        fields = [
            "System.Id", "System.Title", "System.State", "System.AssignedTo",
            "System.Tags", "System.AreaPath", "System.WorkItemType",
            "Microsoft.VSTS.Scheduling.StartDate",
            "Microsoft.VSTS.Scheduling.TargetDate",
            "Microsoft.VSTS.Common.Priority",
            "Custom.PI",
            "Custom.ScrumTeamOwnership",
            "Custom.SolutionOwner",
            "Custom.DependantScrumTeam",
            "Custom.PlannedDevEffort",
            "Custom.PlannedQAEffort",
        ]
        return self.get_wi_batch(ids, fields)

    def get_child_tasks(self, proj, feature_ids):
        """Get all Tasks/Bugs under the given feature IDs — HRM only"""
        if not feature_ids:
            return []
        id_list = ", ".join(str(i) for i in feature_ids)
        q = f"""SELECT [System.Id] FROM WorkItems
                WHERE [System.TeamProject] = 'HRM'
                AND [System.WorkItemType] IN ('Task','Bug')
                AND [System.Parent] IN ({id_list})"""
        ids = self._wiql(proj, q)
        return self.get_wi_batch(ids)

# ─────────────────────────────────────────────────────────────────
# SPRINT HELPERS (unchanged logic, same as v6)
# ─────────────────────────────────────────────────────────────────
def detect_blocked(tags):
    if not tags:
        return []
    tlist = [t.strip() for t in str(tags).split(";")]
    if "Blocked" not in tlist:
        return []
    matched = [(s, BLOCKED_TAGS[s]) for s in ["Env-Unstable", "PR-Approval", "Test-Data-Issue"] if s in tlist]
    return matched or [("Blocked", BLOCKED_TAGS["Blocked"])]

def check_dates(is_, it, ss, se):
    v = []
    if not is_:
        v.append("Start date not set")
    elif ss and is_ < ss:
        v.append(f"Start {is_.strftime('%b %d')} before sprint start")
    elif se and is_ > se:
        v.append(f"Start {is_.strftime('%b %d')} after sprint end")
    if not it:
        v.append("Target date not set")
    elif se and it > se:
        v.append(f"Target {it.strftime('%b %d')} beyond sprint end")
    return v

def classify_spill(item, hl):
    state = item.get("state", "")
    est = item.get("est", 0) or 0
    done = item.get("done", 0) or 0
    rem = item.get("rem", 0) or 0
    if state in COMPLETED:
        return "none", []
    total = done + rem
    prog = (done / total) if total > 0 else 0
    risk = "none"; reasons = []
    if state == "On hold":
        risk = "high"; reasons.append("Blocked — On Hold")
    if state == "To Do" and rem > hl and hl > 0:
        risk = "high"; reasons.append(f"Not started · {rem}h needed, {hl}h left")
    if state == "Scheduled" and rem > hl and hl > 0:
        risk = "high"; reasons.append(f"Scheduled · {rem}h rem > {hl}h left")
    td = item.get("target_date"); se = item.get("sprint_end")
    if td and se and td > se:
        risk = "high"; reasons.append(f"Target {td.strftime('%b %d')} past sprint end")
    if risk != "high":
        if state == "To Do" and 0 < rem <= hl and rem > 4:
            risk = "watch"; reasons.append(f"Not started · {rem}h remaining")
        if state == "In Progress" and total > 4 and prog < 0.3:
            risk = "watch"; reasons.append(f"Only {int(prog*100)}% complete")
        if state == "In Progress" and done == 0 and rem > 0:
            risk = "watch"; reasons.append("In Progress — 0 hours logged")
        if state == "Scheduled":
            risk = "watch"; reasons.append("Scheduled — not activated")
        if state == "In Progress" and hl > 0 and rem > (hl * 0.8):
            risk = "watch"; reasons.append(f"{rem}h rem, limited time left")
    return risk, reasons

def classify_overburn(item):
    state = item.get("state", "")
    est = item.get("est", 0) or 0
    done = item.get("done", 0) or 0
    rem = item.get("rem", 0) or 0
    if est <= 0:
        return False, 0, done
    if state in COMPLETED:
        ov = done - est
        return ov > 0, round(max(ov, 0), 1), round(done, 1)
    elif state in INPROGRESS:
        proj = done + rem
        ov = proj - est
        return ov > 0, round(max(ov, 0), 1), round(proj, 1)
    return False, 0, done

def hour_completion_pct(items):
    total_est  = sum(i.get("est", 0) or 0 for i in items)
    total_done = sum(i.get("done", 0) or 0 for i in items)
    if total_est <= 0:
        return 0
    return min(round(total_done / total_est * 100), 100)

def member_risk_score(items):
    return (
        sum(3 if i.get("spill_risk") == "high" else 1 if i.get("spill_risk") == "watch" else 0 for i in items)
        + sum(2 for i in items if i.get("is_overburn"))
        + sum(1 for i in items if i.get("is_blocked"))
    )

def compute_health(items):
    tasks = [i for i in items if i.get("type") in VALID_TYPES] or items
    n = len(tasks)
    dc = sum(1 for i in tasks if i["state"] in COMPLETED)
    hc = sum(1 for i in tasks if i.get("spill_risk") == "high")
    wc = sum(1 for i in tasks if i.get("spill_risk") == "watch")
    oc = sum(1 for i in tasks if i.get("is_overburn"))
    bc = sum(1 for i in tasks if i.get("is_blocked"))
    unc = sum(1 for i in tasks if i.get("is_unestimated"))
    dic = sum(1 for i in tasks if i.get("has_date_issue"))
    cp = hour_completion_pct(tasks)
    op = round(oc / n * 100) if n else 0
    if hc >= 3 or op >= 30 or bc >= 3:
        h = "critical"
    elif hc >= 1 or op >= 15 or bc >= 1:
        h = "atrisk"
    elif wc >= 1 or oc > 0:
        h = "watch"
    else:
        h = "healthy"
    return {"health": h, "total": n, "done_count": dc, "high_count": hc, "watch_count": wc,
            "over_count": oc, "blocked_count": bc, "unest_count": unc, "date_issue_count": dic, "comp_pct": cp}

# ─────────────────────────────────────────────────────────────────
# SPRINT DATA LOADER
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def load_team(org, proj, pat, team):
    cl = DevOpsClient(org, pat)
    sp = cl.get_sprint(proj, team)
    if not sp:
        return {"team": team, "error": "No sprint found", "items": [], "health": "no_data",
                "total": 0, "done_count": 0, "high_count": 0, "watch_count": 0, "over_count": 0,
                "blocked_count": 0, "unest_count": 0, "date_issue_count": 0, "comp_pct": 0}
    attrs = sp.get("attributes", {}); sname = sp.get("name", ""); tf = sp.get("_tf", "current")
    ss = pd_(attrs.get("startDate")); se = pd_(attrs.get("finishDate"))
    hl = working_hours_remaining(se); dl = working_days_remaining(se)
    ids = cl.get_wi_ids_for_sprint(proj, team, sp.get("id", ""))
    if not ids:
        h = compute_health([])
        return {"team": team, "sprint_name": sname, "timeframe": tf, "sprint_start": ss,
                "sprint_end": se, "hrs_left": hl, "days_left": dl, "items": [], "error": None, **h}
    raw = cl.get_wi_batch(ids); pids = set(); items = []
    for wi in raw:
        f = wi.get("fields", {})
        wt = f.get("System.WorkItemType", "")
        if wt not in VALID_TYPES:
            continue
        af = f.get("System.AssignedTo", {})
        assignee = af.get("displayName", "Unassigned") if isinstance(af, dict) else str(af or "Unassigned")
        pid = f.get("System.Parent")
        if pid:
            pids.add(pid)
        tags = f.get("System.Tags", "") or ""
        is_ = pd_(f.get("Microsoft.VSTS.Scheduling.StartDate"))
        it  = pd_(f.get("Microsoft.VSTS.Scheduling.TargetDate"))
        item = {
            "id": wi.get("id"), "title": f.get("System.Title", ""), "type": wt,
            "state": f.get("System.State", ""), "assignee": assignee,
            "est": f.get("Microsoft.VSTS.Scheduling.OriginalEstimate") or 0,
            "done": f.get("Microsoft.VSTS.Scheduling.CompletedWork") or 0,
            "rem": f.get("Microsoft.VSTS.Scheduling.RemainingWork") or 0,
            "priority": f.get("Microsoft.VSTS.Common.Priority", 3),
            "tags": tags, "item_start": is_, "item_target": it, "parent_id": pid,
            "sprint_name": sname, "sprint_start": ss, "sprint_end": se, "team": team, "timeframe": tf,
            "devops_url": f"{org}/{proj}/_workitems/edit/{wi.get('id')}",
            "backlog_title": "", "backlog_url": "#", "feature_title": "", "feature_url": "#",
        }
        sr, rr = classify_spill(item, hl)
        iso, ov, pj = classify_overburn(item)
        bt = detect_blocked(tags); dv = check_dates(is_, it, ss, se)
        item.update({
            "spill_risk": sr, "spill_reasons": rr, "is_overburn": iso, "overrun": ov, "projected": pj,
            "blocked_tags": bt, "is_blocked": len(bt) > 0, "date_violations": dv,
            "has_date_issue": len(dv) > 0,
            "is_unestimated": (item["est"] or 0) == 0 and item["state"] not in COMPLETED,
        })
        items.append(item)
    if pids:
        parents = cl.get_wi_batch(list(pids)); gids = set(); pmap = {}
        for p in parents:
            f = p.get("fields", {}); pid2 = p.get("id")
            pmap[pid2] = {"title": f.get("System.Title", ""), "parent_id": f.get("System.Parent"),
                          "url": f"{org}/{proj}/_workitems/edit/{pid2}"}
            if f.get("System.Parent"):
                gids.add(f["System.Parent"])
        gpmap = {}
        if gids:
            for gp in cl.get_wi_batch(list(gids)):
                f = gp.get("fields", {}); gpid = gp.get("id")
                gpmap[gpid] = {"title": f.get("System.Title", ""), "url": f"{org}/{proj}/_workitems/edit/{gpid}"}
        for item in items:
            pid = item.get("parent_id")
            if pid and pid in pmap:
                item["backlog_title"] = pmap[pid]["title"]; item["backlog_url"] = pmap[pid]["url"]
                gpid = pmap[pid].get("parent_id")
                if gpid and gpid in gpmap:
                    item["feature_title"] = gpmap[gpid]["title"]; item["feature_url"] = gpmap[gpid]["url"]
    h = compute_health(items)
    return {"team": team, "sprint_name": sname, "timeframe": tf, "sprint_start": ss,
            "sprint_end": se, "hrs_left": hl, "days_left": dl, "items": items, "error": None, **h}

# ─────────────────────────────────────────────────────────────────
# PI DATA LOADER
# ─────────────────────────────────────────────────────────────────
def load_pi_data(org, pat, pi_name, pi_field="Custom.PI", _cache_v=0):
    cl = DevOpsClient(org, pat)
    result = {"pi_name": pi_name, "epics": [], "features": [], "pi_start": None, "pi_end": None,
              "total_working_days": 0, "remaining_working_days": 0}

    # ── Get PI Epic dates from Azure DevOps ──
    epic_ids = cl.get_pi_epics("HRM", pi_name) or []
    if epic_ids:
        epics = cl.get_wi_batch(epic_ids, [
            "System.Id", "System.Title", "System.State",
            "System.IterationPath", "System.AreaPath",
            "Microsoft.VSTS.Scheduling.StartDate",
            "Microsoft.VSTS.Scheduling.TargetDate",
        ])
        result["epics"] = epics
        for e in epics:
            f = e.get("fields", {})
            s  = pd_(f.get("Microsoft.VSTS.Scheduling.StartDate"))
            e2 = pd_(f.get("Microsoft.VSTS.Scheduling.TargetDate"))
            if s and e2:
                result["pi_start"] = s
                result["pi_end"]   = e2
                result["total_working_days"]     = working_days_between(s, e2)
                result["remaining_working_days"] = working_days_remaining(e2)
                break

    # ── Get Features — HRM only, strictly Feature type, exclude Epic IDs ──
    all_features = []
    epic_ids_set = set(epic_ids)  # never include these in feature list
    feats = cl.get_features_for_pi("HRM", pi_name)
    # Store raw count before filtering for debug
    result["_raw_count"] = len(feats)
    result["_sample_state"] = feats[0].get("fields",{}).get("System.State","?") if feats else "no features"
    for f in feats:
        # Double-safety: exclude any Epic IDs and non-Feature types
        if f.get("id") in epic_ids_set:
            continue
        fields      = f.get("fields", {})
        wi_type     = fields.get("System.WorkItemType", "")
        if wi_type and wi_type != "Feature":
            continue
        fields      = f.get("fields", {})
        raw_state    = fields.get("System.State", "")
        consolidated = PI_STATUS_MAP.get(raw_state)
        if not consolidated:
            continue  # Skip features not in approved status list
        af       = fields.get("System.AssignedTo", {})
        assignee = af.get("displayName", "Unassigned") if isinstance(af, dict) else str(af or "Unassigned")
        # Extract planned effort — try multiple possible field names
        def _ef(flds, *keys):
            for k in keys:
                v = flds.get(k)
                if v is not None:
                    try: return float(v)
                    except: pass
            return 0.0
        pdev = _ef(fields, "Custom.PlannedDevEffort", "Custom.Dev")
        pqa  = _ef(fields, "Custom.PlannedQAEffort",  "Custom.QA")
        # Scrum team ownership
        st_raw = fields.get("Custom.ScrumTeamOwnership", "") or ""
        # Normalise to our known team names
        scrum_team = st_raw.strip() if st_raw else "—"
        dep_raw = fields.get("Custom.DependantScrumTeam", "") or ""
        dep_team = dep_raw.strip() if dep_raw else "—"
        sol_owner_raw = fields.get("Custom.SolutionOwner", {})
        if isinstance(sol_owner_raw, dict):
            sol_owner = sol_owner_raw.get("displayName", "—")
        else:
            sol_owner = str(sol_owner_raw) if sol_owner_raw else "—"
        feat_obj = {
            "id":             f.get("id"),
            "title":          fields.get("System.Title", ""),
            "state":          raw_state,
            "status":         consolidated,
            "assignee":       assignee,
            "priority":       fields.get("Microsoft.VSTS.Common.Priority", 99),
            "pi_priority":    0,
            "po_priority":    fields.get("Custom.POLevelPriority", 0) or 0,
            "tags":           fields.get("System.Tags", "") or "",
            "area":           fields.get("System.AreaPath", ""),
            "project":        "HRM",
            "start_date":     pd_(fields.get("Microsoft.VSTS.Scheduling.StartDate")),
            "end_date":       pd_(fields.get("Microsoft.VSTS.Scheduling.TargetDate")),
            "devops_url":     f"{org}/HRM/_workitems/edit/{f.get('id')}",
            "scrum_team":     scrum_team,
            "dep_team":       dep_team,
            "solution_owner": sol_owner,
            "pdev":           pdev,
            "pqa":            pqa,
            "est": 0, "done": 0, "rem": 0,
            "task_count": 0, "done_count": 0,
        }
        all_features.append(feat_obj)
    result["features"] = all_features
    return result

# ─────────────────────────────────────────────────────────────────
# PM CHECK — read comments for action items
# ─────────────────────────────────────────────────────────────────
ACTION_KEYWORDS = ["delay", "delayed", "critical", "blocker", "blocked", "high estimation",
                   "dependency", "dependent", "urgent", "escalate", "overdue", "risk",
                   "ishan", "rohan"]

def analyse_comment_for_pm(comment_text, author):
    text_lower = comment_text.lower()
    triggers = [kw for kw in ACTION_KEYWORDS if kw in text_lower]
    pm_lower  = PM_NAME.lower().split()
    mentioned = any(part in text_lower for part in pm_lower) or "janarthan" in text_lower
    from_key_person = any(name in (author or "").lower() for name in ["ishan", "rohan"])
    if triggers or (from_key_person and mentioned):
        return {"triggers": triggers, "from_key_person": from_key_person, "mentioned_pm": mentioned}
    return None

@st.cache_data(ttl=300, show_spinner=False)
def load_pm_action_items(org, pat, all_data):
    cl = DevOpsClient(org, pat)
    actions = []
    for td in all_data:
        for item in td.get("items", []):
            if item.get("state") in COMPLETED:
                continue
            wi_id = item.get("id"); proj = "HRM"
            comments = cl.get_comments(proj, wi_id)
            for c in comments:
                text   = re.sub(r'<[^>]+>', '', c.get("text", ""))
                author_obj = c.get("createdBy", {})
                author = author_obj.get("displayName", "") if isinstance(author_obj, dict) else str(author_obj)
                analysis = analyse_comment_for_pm(text, author)
                if analysis:
                    actions.append({
                        "wi_id":    wi_id,
                        "title":    item.get("title", ""),
                        "team":     item.get("team", ""),
                        "author":   author,
                        "comment":  text[:300],
                        "triggers": analysis["triggers"],
                        "from_key": analysis["from_key_person"],
                        "devops_url": item.get("devops_url", ""),
                    })
    return actions

# ─────────────────────────────────────────────────────────────────
# DEMO DATA GENERATORS
# ─────────────────────────────────────────────────────────────────
def gen_demo_sprint():
    from random import seed, randint, choice, random, uniform
    seed(42); today = date.today()
    cfgs = {
        "Echo Engineers":   {"h": 3, "w": 4, "o": 5, "b": 2, "dp": 0.42, "ss": date(2026, 5, 4), "se": date(2026, 5, 15)},
        "Code Commanders":  {"h": 1, "w": 3, "o": 3, "b": 1, "dp": 0.60, "ss": date(2026, 5, 4), "se": date(2026, 5, 15)},
        "Beta Brigade":     {"h": 2, "w": 2, "o": 4, "b": 2, "dp": 0.48, "ss": date(2026, 4, 27), "se": date(2026, 5, 8)},
        "Gamma Guardians":  {"h": 0, "w": 2, "o": 2, "b": 0, "dp": 0.72, "ss": date(2026, 5, 4), "se": date(2026, 5, 15)},
        "Hyper Hackers":    {"h": 0, "w": 0, "o": 0, "b": 0, "dp": 0.90, "ss": date(2026, 4, 27), "se": date(2026, 5, 8)},
    }
    feats  = ["Employee Info Module v2", "Payroll Engine", "Leave Management", "Performance Portal", "Recruitment Flow"]
    bls    = ["API Layer", "Test Coverage", "UI Revamp", "Data Migration", "Integration Testing", "Documentation"]
    mems   = {
        "Echo Engineers":   ["A.F.", "C.B.", "H.G.", "S.N.", "U.W.", "L.R."],
        "Code Commanders":  ["K.B.", "P.G.", "N.L.", "M.P.", "I.U.", "M.R."],
        "Beta Brigade":     ["S.E.", "M.G.", "L.G.", "A.K.", "P.M.", "S.T."],
        "Gamma Guardians":  ["N.R.", "C.W.", "O.B.", "T.L.", "D.S.", "K.H."],
        "Hyper Hackers":    ["R.P.", "F.A.", "T.B.", "S.L.", "M.X.", "J.K."],
    }
    btags = ["Blocked; Env-Unstable", "Blocked; PR-Approval", "Blocked; Test-Data-Issue"]
    all_data = []; iid = 130000
    for team, cfg in cfgs.items():
        items = []; n = randint(20, 28); tm = mems[team]
        ss = cfg["ss"]; se = cfg["se"]
        hl = working_hours_remaining(se); dl = working_days_remaining(se)
        tf = "current" if today <= se else "past"
        sp_name = f"26R1_SP{'06' if tf == 'current' else '05'}"
        for j in range(n):
            iid += 1; feat = feats[j % 5]; bl = bls[j % 6]; mem = tm[j % len(tm)]
            is_h = j < cfg["h"]; is_w = cfg["h"] <= j < cfg["h"] + cfg["w"]
            is_o = j < cfg["o"]; is_b = j < cfg["b"]; is_d = random() < cfg["dp"]
            if is_d:   state = choice(["Done", "Done", "Resolved", "Dev Completed"])
            elif is_h: state = choice(["To Do", "On hold", "Scheduled"])
            elif is_w: state = choice(["In Progress", "To Do"])
            else:      state = choice(["To Do", "In Progress", "Done"])
            est = round(randint(2, 16) * 0.5, 1) if j % 8 != 0 else 0
            if state in COMPLETED:
                dh = round(est * (1.3 if is_o else uniform(0.7, 1.0)), 1) if est > 0 else round(uniform(1, 8), 1); rh = 0
            elif state == "In Progress":
                dh = round(est * uniform(0.1, 0.5), 1) if est > 0 else 0
                rh = round((est * 1.4 - dh) if is_o else max(est - dh + uniform(0, 2), 0), 1) if est > 0 else round(uniform(2, 8), 1)
            else:
                dh = 0; rh = est if not is_h else round(est + randint(8, 20), 1)
            tags = choice(btags) if (is_b and state not in COMPLETED) else "26R1"
            is__ = ss if j % 10 != 0 else None
            it_  = se if j % 10 != 0 and j % 13 != 0 else (date(2026, 5, 30) if j % 13 == 0 else None)
            item = {
                "id": iid, "title": f"[{'DEV' if j%3==0 else 'QA' if j%3==1 else 'BA'}] {bl} — {feat[:35]}",
                "type": choice(["Task", "Task", "Task", "Bug"]), "state": state, "assignee": mem,
                "est": est, "done": round(dh, 1), "rem": round(max(rh, 0), 1),
                "priority": randint(1, 3), "tags": tags, "item_start": is__, "item_target": it_,
                "parent_id": 120000 + j, "sprint_name": sp_name, "sprint_start": ss, "sprint_end": se,
                "team": team, "timeframe": tf,
                "devops_url": f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{iid}",
                "backlog_title": bl, "backlog_url": f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{120000+j}",
                "feature_title": feat, "feature_url": f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{110000+(j%5)}",
            }
            sr, rr = classify_spill(item, hl); iso, ov, pj = classify_overburn(item)
            bt = detect_blocked(tags); dv = check_dates(is__, it_, ss, se)
            item.update({
                "spill_risk": sr, "spill_reasons": rr, "is_overburn": iso, "overrun": ov, "projected": pj,
                "blocked_tags": bt, "is_blocked": len(bt) > 0, "date_violations": dv,
                "has_date_issue": len(dv) > 0,
                "is_unestimated": (est or 0) == 0 and state not in COMPLETED,
            })
            items.append(item)
        h = compute_health(items)
        all_data.append({"team": team, "sprint_name": sp_name, "timeframe": tf, "sprint_start": ss,
                         "sprint_end": se, "hrs_left": hl, "days_left": dl, "items": items, "error": None, **h})
    return all_data

def gen_demo_pi():
    today = date.today()
    features = [
        {"id": 110001, "title": "Employee Info Module v2",  "state": "Dev In Progress",     "status": "Development",     "assignee": "Team A", "priority": 1, "pi_priority": 1,  "po_priority": 2,  "project": "HRM",        "start_date": date(2026,1,5),  "end_date": date(2026,3,31), "est": 320, "done": 290, "rem": 30,  "task_count": 18, "done_count": 15, "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110001", "tags": "26R1", "area": "HRM\\Echo Engineers", "scrum_team": "Echo Engineers",  "dep_team": "—",             "solution_owner": "Aravinda K.", "pdev": 280, "pqa": 60, "scrum_team": "Echo Engineers", "dep_team": "—", "solution_owner": "Aravinda K.", "pdev": 280, "pqa": 60},
        {"id": 110002, "title": "Payroll Engine",            "state": "QA In Progress",      "status": "Testing",         "assignee": "Team B", "priority": 1, "pi_priority": 2,  "po_priority": 1,  "project": "HRM",        "start_date": date(2026,1,5),  "end_date": date(2026,5,15), "est": 480, "done": 200, "rem": 340, "task_count": 24, "done_count": 10, "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110002", "tags": "26R1", "area": "HRM\\Code Commanders", "scrum_team": "Code Commanders", "dep_team": "Echo Engineers", "solution_owner": "Kasun B.", "pdev": 350, "pqa": 80},
        {"id": 110003, "title": "Leave Management",          "state": "QA Pending",          "status": "Testing",         "assignee": "Team C", "priority": 2, "pi_priority": 3,  "po_priority": 3,  "project": "HRM",        "start_date": date(2026,2,1),  "end_date": date(2026,5,22), "est": 280, "done": 170, "rem": 150, "task_count": 16, "done_count": 9,  "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110003", "tags": "26R1", "area": "HRM\\Beta Brigade", "scrum_team": "Beta Brigade", "dep_team": "—", "solution_owner": "Sharini N.", "pdev": 200, "pqa": 60},
        {"id": 110004, "title": "Performance Portal",        "state": "Dev Completed",       "status": "Development",     "assignee": "Team D", "priority": 2, "pi_priority": 4,  "po_priority": 4,  "project": "HRM",        "start_date": date(2026,1,5),  "end_date": date(2026,5,15), "est": 240, "done": 220, "rem": 10,  "task_count": 14, "done_count": 13, "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110004", "tags": "26R1", "area": "HRM\\Gamma Guardians", "scrum_team": "Gamma Guardians", "dep_team": "—", "solution_owner": "Nadia R.", "pdev": 180, "pqa": 50},
        {"id": 110005, "title": "Recruitment Flow",          "state": "Dev In Progress",     "status": "Development",     "assignee": "Team E", "priority": 2, "pi_priority": 5,  "po_priority": 5,  "project": "HRM",        "start_date": date(2026,2,15), "end_date": date(2026,6,5),  "est": 360, "done": 136, "rem": 280, "task_count": 20, "done_count": 7,  "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110005", "tags": "26R1", "area": "HRM\\Hyper Hackers", "scrum_team": "Hyper Hackers", "dep_team": "Code Commanders", "solution_owner": "Janaka K.", "pdev": 260, "pqa": 80},
        {"id": 110007, "title": "Reporting Module",          "state": "Dev In Progress",     "status": "Development",     "assignee": "Team A", "priority": 3, "pi_priority": 7,  "po_priority": 7,  "project": "HRM",        "start_date": date(2026,3,15), "end_date": date(2026,6,5),  "est": 180, "done": 90,  "rem": 110, "task_count": 10, "done_count": 5,  "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110007", "tags": "26R1", "area": "HRM\\Echo Engineers", "scrum_team": "Echo Engineers", "dep_team": "—", "solution_owner": "Chamod B.", "pdev": 140, "pqa": 40},
        {"id": 110008, "title": "Data Migration Scripts",   "state": "Release Ready",        "status": "Release Ready",   "assignee": "Team B", "priority": 1, "pi_priority": 8,  "po_priority": 3,  "project": "HRM",        "start_date": date(2026,1,5),  "end_date": date(2026,4,30), "est": 120, "done": 118, "rem": 0,   "task_count": 8,  "done_count": 8,  "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110008", "tags": "26R1", "area": "HRM\\Code Commanders", "scrum_team": "Code Commanders", "dep_team": "—", "solution_owner": "Praveena G.", "pdev": 80, "pqa": 20},
        {"id": 110009, "title": "SSO Integration",           "state": "Done",                "status": "Done",            "assignee": "Team C", "priority": 2, "pi_priority": 9,  "po_priority": 8,  "project": "HRM",        "start_date": date(2026,1,5),  "end_date": date(2026,3,15), "est": 160, "done": 158, "rem": 0,   "task_count": 10, "done_count": 10, "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110009", "tags": "26R1", "area": "HRM\\Beta Brigade", "scrum_team": "Beta Brigade", "dep_team": "—", "solution_owner": "Sammani E.", "pdev": 100, "pqa": 40},
        {"id": 110010, "title": "Mobile App Revamp",         "state": "On hold",             "status": "On Hold",         "assignee": "Team D", "priority": 3, "pi_priority": 10, "po_priority": 9,  "project": "HRM",        "start_date": date(2026,4,1),  "end_date": date(2026,6,5),  "est": 260, "done": 40,  "rem": 240, "task_count": 15, "done_count": 2,  "devops_url": "https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/110010", "tags": "26R1", "area": "HRM\\Gamma Guardians", "scrum_team": "Gamma Guardians", "dep_team": "Code Commanders", "solution_owner": "Chen W.", "pdev": 180, "pqa": 60},
    ]
    return {
        "pi_name": "26R1",
        "pi_start": date(2026, 3, 18),
        "pi_end":   date(2026, 6, 11),
        "total_working_days":     working_days_between(date(2026, 3, 18), date(2026, 6, 11)),
        "remaining_working_days": working_days_remaining(date(2026, 6, 11)),
        "epics": [],
        "features": features,
    }

# ─────────────────────────────────────────────────────────────────
# HTML COMPONENT HELPERS
# ─────────────────────────────────────────────────────────────────
def card_open(border_top_color=None, extra_style=""):
    top = f"border-top:3px solid {border_top_color};" if border_top_color else ""
    return f'<div style="background:#ffffff;border:1px solid #e8ecf0;border-radius:10px;padding:16px;{top}{extra_style}">'

def card_close():
    return '</div>'

def pill(text, color, bg, border=None):
    bd = f"border:1px solid {border};" if border else ""
    return f'<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;background:{bg};color:{color};{bd}">{text}</span>'

def progress_bar(pct, color, height=6):
    return f'''<div style="background:#f3f4f6;border-radius:4px;height:{height}px;overflow:hidden;margin:4px 0">
<div style="width:{pct}%;height:100%;background:{color};border-radius:4px;transition:width .4s"></div></div>'''

def section_header(title, subtitle=""):
    sub = f'<div style="font-size:12px;color:#6b7280;margin-top:2px">{subtitle}</div>' if subtitle else ""
    return f'<div style="margin-bottom:12px"><div style="font-size:15px;font-weight:700;color:#1a202c">{title}</div>{sub}</div>'

def metric_html(label, value, sub="", value_color="#1a202c"):
    return f'''<div style="background:#ffffff;border:1px solid #e8ecf0;border-radius:8px;padding:12px 14px">
<div style="font-size:11px;font-weight:600;color:#6b7280;margin-bottom:4px">{label}</div>
<div style="font-size:24px;font-weight:800;color:{value_color};line-height:1">{value}</div>
{f'<div style="font-size:11px;color:#6b7280;margin-top:4px">{sub}</div>' if sub else ""}
</div>'''

def status_badge(health):
    s = STATUS.get(health, STATUS["no_data"])
    return f'<span style="background:{s["bg"]};color:{s["color"]};border:1px solid {s["border"]};border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700">{s["icon"]} {s["text"].upper()}</span>'

def pi_status_badge(status):
    sc = PI_STATUS_COLORS.get(status, {"bg": "#f9fafb", "color": "#6b7280", "border": "#e5e7eb"})
    return f'<span style="background:{sc["bg"]};color:{sc["color"]};border:1px solid {sc["border"]};border-radius:12px;padding:2px 10px;font-size:11px;font-weight:600">{status}</span>'

# ─────────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ─────────────────────────────────────────────────────────────────
def build_excel(all_data):
    rows = []
    for t in all_data:
        for i in t.get("items", []):
            rows.append({
                "Work Item ID": i.get("id"), "Title": i.get("title", ""), "Type": i.get("type", ""),
                "State": i.get("state", ""), "Assigned To": i.get("assignee", ""), "Team": t.get("team", ""),
                "Sprint": i.get("sprint_name", ""), "Sprint Start": str(i.get("sprint_start", "")),
                "Sprint End": str(i.get("sprint_end", "")), "Original Est (h)": i.get("est", 0),
                "Completed (h)": i.get("done", 0), "Remaining (h)": i.get("rem", 0),
                "Projected (h)": i.get("projected", 0),
                "Spill Risk": i.get("spill_risk", "none").upper(),
                "Spill Reasons": " | ".join(i.get("spill_reasons", [])),
                "Is Overburn": "YES" if i.get("is_overburn") else "NO",
                "Overrun (h)": i.get("overrun", 0),
                "Is Blocked": "YES" if i.get("is_blocked") else "NO",
                "Blocked Tags": i.get("tags", ""),
                "Is Unestimated": "YES" if i.get("is_unestimated") else "NO",
                "Date Violation": "YES" if i.get("has_date_issue") else "NO",
                "Date Issues": " | ".join(i.get("date_violations", [])),
                "Item Start": str(i.get("item_start", "")),
                "Item Target": str(i.get("item_target", "")),
                "Feature": i.get("feature_title", ""), "Backlog Item": i.get("backlog_title", ""),
                "DevOps URL": i.get("devops_url", ""),
            })
    df = pd.DataFrame(rows); buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Sprint Data")
        ws = w.sheets["Sprint Data"]
        for col in ws.columns:
            ml = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(ml + 4, 55)
    buf.seek(0); return buf


# ─────────────────────────────────────────────────────────────────
# PI FEATURE CHILD TASK LOADER
# ─────────────────────────────────────────────────────────────────
COMPLETED_STATES = ["Done", "Resolved", "Dev Completed"]

# Activities that count — Documentation/DevOps excluded
DEV_ACTIVITIES = {"Development"}
QA_ACTIVITIES  = {"Testing"}

# Completed feature states for team box calculation
FEATURE_COMPLETED_STATES = {
    "Release Materials Pending", "Release Materials In-Progress",
    "Release Materials Completed", "Release Ready", "Done"
}

@st.cache_data(ttl=600, show_spinner=False)
def load_feature_tasks(org, pat, feature_ids):
    """Load all child tasks/bugs for a list of feature IDs and compute effort metrics."""
    if not feature_ids:
        return {}
    cl = DevOpsClient(org, pat)
    # Fetch all child items via WIQL
    id_list = ", ".join(str(i) for i in feature_ids)
    q = f"""SELECT [System.Id] FROM WorkItems
            WHERE [System.TeamProject] = 'HRM'
            AND [System.WorkItemType] IN ('Task','Bug')
            AND [System.Parent] IN ({id_list})"""
    task_ids = cl._wiql("HRM", q)
    if not task_ids:
        return {fid: {"tasks": [], "dev_actual": 0, "qa_actual": 0, "bug_count": 0} for fid in feature_ids}

    raw = cl.get_wi_batch(task_ids, [
        "System.Id", "System.Title", "System.WorkItemType", "System.State",
        "System.AssignedTo", "System.Parent",
        "Microsoft.VSTS.Common.Activity",
        "Microsoft.VSTS.Scheduling.OriginalEstimate",
        "Microsoft.VSTS.Scheduling.CompletedWork",
        "Microsoft.VSTS.Scheduling.RemainingWork",
    ])

    # Group by parent feature
    result = {fid: {"tasks": [], "dev_actual": 0, "qa_actual": 0, "bug_count": 0} for fid in feature_ids}
    for wi in raw:
        f = wi.get("fields", {})
        parent_id = f.get("System.Parent")
        if parent_id not in result:
            continue
        wi_type  = f.get("System.WorkItemType", "")
        activity = f.get("Microsoft.VSTS.Common.Activity", "") or ""
        state    = f.get("System.State", "")
        est      = f.get("Microsoft.VSTS.Scheduling.OriginalEstimate") or 0
        done     = f.get("Microsoft.VSTS.Scheduling.CompletedWork") or 0
        rem      = f.get("Microsoft.VSTS.Scheduling.RemainingWork") or 0
        af       = f.get("System.AssignedTo", {})
        assignee = af.get("displayName", "Unassigned") if isinstance(af, dict) else str(af or "Unassigned")

        task_obj = {
            "id":       wi.get("id"),
            "title":    f.get("System.Title", ""),
            "type":     wi_type,
            "state":    state,
            "assignee": assignee,
            "activity": activity,
            "est":      est,
            "done":     done,
            "rem":      rem,
            "actual":   round(done + rem, 1),
            "devops_url": f"{st.session_state.get('org_url','')}/HRM/_workitems/edit/{wi.get('id')}",
        }
        result[parent_id]["tasks"].append(task_obj)

        # Effort calculations — exclude Documentation/DevOps
        if wi_type == "Bug":
            result[parent_id]["bug_count"] += 1
            # Bugs count as Dev effort
            result[parent_id]["dev_actual"] = round(result[parent_id]["dev_actual"] + done + rem, 1)
        elif activity in DEV_ACTIVITIES:
            result[parent_id]["dev_actual"] = round(result[parent_id]["dev_actual"] + done + rem, 1)
        elif activity in QA_ACTIVITIES:
            result[parent_id]["qa_actual"]  = round(result[parent_id]["qa_actual"]  + done + rem, 1)
        # Documentation, DevOps, etc. → excluded

    return result


def build_feature_excel(features, task_data):
    """Build Excel export for feature list with tasks."""
    feat_rows = []
    for f in features:
        td = task_data.get(f["id"], {})
        odev = round(td.get("dev_actual", 0) - f.get("pdev", 0), 1)
        oqa  = round(td.get("qa_actual", 0)  - f.get("pqa", 0), 1)
        feat_rows.append({
            "PI Priority #":      f.get("pi_priority", ""),
            "Feature ID":         f.get("id", ""),
            "Title":              f.get("title", ""),
            "State":              f.get("state", ""),
            "Solution Owner":     f.get("solution_owner", ""),
            "Scrum Team":         f.get("scrum_team", ""),
            "Dependent Team":     f.get("dep_team", ""),
            "Planned Dev (h)":    f.get("pdev", 0),
            "Actual Dev (h)":     td.get("dev_actual", 0),
            "Overrun Dev (h)":    max(odev, 0),
            "Planned QA (h)":     f.get("pqa", 0),
            "Actual QA (h)":      td.get("qa_actual", 0),
            "Overrun QA (h)":     max(oqa, 0),
            "Total Bugs":         td.get("bug_count", 0),
            "DevOps URL":         f.get("devops_url", ""),
        })
    buf = BytesIO()
    pd.DataFrame(feat_rows).to_excel(buf, index=False, sheet_name="Feature Board")
    buf.seek(0)
    return buf


def build_task_excel(feature, tasks):
    """Build Excel for tasks under a single feature."""
    rows = []
    for t in tasks:
        if t.get("activity") in ("Documentation",) or (t.get("activity") not in DEV_ACTIVITIES and t.get("activity") not in QA_ACTIVITIES and t.get("type") != "Bug"):
            pass  # include all tasks in download even if excluded from calcs
        rows.append({
            "Item ID":   t.get("id"),
            "Type":      t.get("type"),
            "Title":     t.get("title"),
            "Assignee":  t.get("assignee"),
            "Activity":  t.get("activity"),
            "State":     t.get("state"),
            "Est (h)":   t.get("est", 0),
            "Done (h)":  t.get("done", 0),
            "Rem (h)":   t.get("rem", 0),
            "Actual (h)":t.get("actual", 0),
        })
    buf = BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False, sheet_name=f"Tasks_{feature['id']}")
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────
# PI EXECUTION CENTRE — FULL RENDER (new version)
# ─────────────────────────────────────────────────────────────────
def render_pi_tab(pi_data, all_sprint_data):
    features  = pi_data.get("features", [])
    pi_name   = pi_data.get("pi_name", "—")
    pi_start  = pi_data.get("pi_start")
    pi_end    = pi_data.get("pi_end")
    total_wd  = pi_data.get("total_working_days", 0)
    remain_wd = pi_data.get("remaining_working_days", 0)

    # ── Sprint-level aggregates ──
    all_items    = [i for td in all_sprint_data for i in td.get("items", [])]
    total_est    = sum(i.get("est", 0) or 0 for i in all_items)
    total_done   = sum(i.get("done", 0) or 0 for i in all_items)
    comp_pct     = min(round(total_done / total_est * 100), 100) if total_est > 0 else 0
    spill_high   = [i for i in all_items if i.get("spill_risk") == "high"]
    spill_watch  = [i for i in all_items if i.get("spill_risk") == "watch"]
    overburn_all = [i for i in all_items if i.get("is_overburn")]
    blocked_all  = [i for i in all_items if i.get("is_blocked")]

    # ── Feature-level aggregates ──
    feat_done_count = sum(1 for f in features if f["status"] == "Done")
    feat_atrisk     = [f for f in features if f["status"] in ["On Hold", "Blocked by Dependent Bugs"]]
    score = max(0, min(100, round(
        100 - len(spill_high)*3 - len(spill_watch)*1
            - len(blocked_all)*2 - len(feat_atrisk)*4
            - max(0, 40 - comp_pct) * 0.5
    )))
    score_color  = "#16a34a" if score >= 75 else "#d97706" if score >= 50 else "#dc2626"
    overall_hlth = "critical" if score < 50 else "atrisk" if score < 70 else "watch" if score < 85 else "healthy"
    os_ = STATUS[overall_hlth]

    # ── Load child task data (live or cached) ──
    org = st.session_state.get("org_url", "")
    pat = st.session_state.get("pat", "")
    feat_ids = [f["id"] for f in features]
    if pat and "YOUR_ORG" not in org and feat_ids:
        task_data = load_feature_tasks(org, pat, feat_ids)
    else:
        task_data = {f["id"]: {"tasks": [], "dev_actual": 0, "qa_actual": 0, "bug_count": 0} for f in features}

    # ── Session state for filters ──
    if "pi_status_filter" not in st.session_state: st.session_state["pi_status_filter"] = None
    if "pi_team_filter"   not in st.session_state: st.session_state["pi_team_filter"]   = None
    if "pi_active_tab"    not in st.session_state: st.session_state["pi_active_tab"]    = "board"
    if "pi_expanded_feat" not in st.session_state: st.session_state["pi_expanded_feat"] = None
    if "pi_sort_col"      not in st.session_state: st.session_state["pi_sort_col"]      = "pi_priority"
    if "pi_sort_asc"      not in st.session_state: st.session_state["pi_sort_asc"]      = True

    # ── HEADER ──
    date_str = f"{pi_start.strftime('%d %b %Y')} → {pi_end.strftime('%d %b %Y')}" if pi_start and pi_end else "—"
    st.markdown(f"""
    <div style="background:#ffffff;border-bottom:1px solid #e8ecf0;padding:12px 20px;
         display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
      <div>
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-size:18px;font-weight:700;color:#1a202c">🚀 PI Execution Centre</span>
          <span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;border-radius:6px;
            padding:2px 10px;font-size:12px;font-weight:600">{pi_name}</span>
          <span style="background:{os_['bg']};color:{os_['color']};border:1px solid {os_['border']};
            border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700">{os_['icon']} {os_['text'].upper()}</span>
        </div>
        <div style="font-size:11px;color:#6b7280;margin-top:3px">
          {date_str} &nbsp;·&nbsp; {total_wd} working days total &nbsp;·&nbsp;
          <span style="color:#dc2626;font-weight:600">{remain_wd} days remaining</span>
          &nbsp;·&nbsp; HRM Project &nbsp;·&nbsp; Updated: {datetime.now().strftime('%d %b %Y %H:%M')}
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <div style="background:{score_color};color:#fff;border-radius:50%;width:46px;height:46px;
             display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:700;flex-shrink:0">
          <div style="font-size:16px;line-height:1">{score}</div>
          <div style="font-size:8px;opacity:.85">SCORE</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Quick action buttons ──
    qa1, qa2, qa3, qa4 = st.columns([1,1,1,5])
    with qa1:
        if st.button("🔃 Refresh data", key="pi_refresh", use_container_width=True):
            st.cache_data.clear()
            st.session_state["cache_version"] = st.session_state.get("cache_version", 0) + 1
            for key in ["pi_loaded","loaded","pi_data","all_data"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    with qa2:
        if st.button("🩺 Run diagnostic", key="pi_diag", use_container_width=True):
            st.session_state["show_pi_diag"] = True
    with qa3:
        if st.button("❌ Hide diag", key="pi_diag_hide", use_container_width=True):
            st.session_state["show_pi_diag"] = False

    # ── Inline diagnostic ──
    if st.session_state.get("show_pi_diag", False):
        org2 = st.session_state.get("org_url","")
        pat2 = st.session_state.get("pat","")
        pi2  = st.session_state.get("current_pi","26R1")
        if pat2 and "YOUR_ORG" not in org2:
            cl2 = DevOpsClient(org2, pat2)
            with st.expander("🩺 Diagnostic results", expanded=True):
                epic_ids2 = cl2.get_pi_epics("HRM", pi2)
                st.write(f"**Epic IDs found:** {epic_ids2}")
                err = st.session_state.get("_wiql_last_error","none")
                st.write(f"**Last WIQL error:** {err}")

                q_feat = f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = 'HRM' AND [System.WorkItemType] = 'Feature' AND [Custom.PI] = '{pi2}'"
                feat_ids2 = cl2._wiql("HRM", q_feat)
                st.write(f"**Features via Custom.PI='{pi2}':** {len(feat_ids2)} found")
                err2 = st.session_state.get("_wiql_last_error","none")
                st.write(f"**Feature query error:** {err2}")

                if not feat_ids2:
                    q_tag = f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = 'HRM' AND [System.WorkItemType] = 'Feature' AND [System.Tags] CONTAINS '{pi2}'"
                    tag_ids = cl2._wiql("HRM", q_tag)
                    st.write(f"**Features via Tags='{pi2}':** {len(tag_ids)} found")

                if feat_ids2:
                    sample2 = cl2.get_wi_batch(feat_ids2[:1], [
                        "System.Id","System.Title","System.State",
                        "Custom.PI","Custom.ScrumTeamOwnership","Custom.PlannedDevEffort"
                    ])
                    if sample2:
                        st.json(sample2[0].get("fields",{}))
        else:
            st.warning("Not connected to Azure DevOps")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── KPI METRICS ROW ──
    total_overrun = sum(i.get("overrun", 0) for i in overburn_all)
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    with k1: st.metric("PI confidence",     f"{score}/100",  "trending ↑" if score>=70 else "trending ↓")
    with k2: st.metric("Feature completion", f"{round(feat_done_count/len(features)*100) if features else 0}%", f"{feat_done_count} of {len(features)} done")
    with k3: st.metric("Sprint completion",  f"{comp_pct}%", f"{total_done:.0f}h / {total_est:.0f}h")
    with k4: st.metric("Spill risk items",   str(len(spill_high)+len(spill_watch)), f"{len(spill_high)} high · {len(spill_watch)} watch")
    with k5: st.metric("Overburn alerts",    str(len(overburn_all)), f"+{total_overrun:.0f}h projected")
    with k6: st.metric("Blocked items",      str(len(blocked_all)), "across 5 teams")

    st.markdown("---")

    # ── FEATURE STATUS BREAKDOWN ──
    st.markdown('<div style="font-size:13px;font-weight:700;color:#1a202c;margin-bottom:10px">Feature status breakdown</div>',
                unsafe_allow_html=True)
    status_order = ["Done","Release Ready","Release Materials","PO Review","Testing","Development",
                    "Solutioning","Grooming","Feature Approval","PI Ready","On Hold","Blocked by Dependent Bugs"]
    status_counts = defaultdict(int)
    for f in features:
        status_counts[f["status"]] += 1

    cols_s1 = st.columns(6)
    cols_s2 = st.columns(6)
    for idx, sname in enumerate(status_order):
        count = status_counts.get(sname, 0)
        sc    = PI_STATUS_COLORS.get(sname, {"bg":"#f9fafb","color":"#6b7280","border":"#e5e7eb"})
        is_active = st.session_state["pi_status_filter"] == sname
        border_style = f"2px solid {sc['color']}" if is_active else f"1px solid {sc['border']}"
        col = (cols_s1 if idx < 6 else cols_s2)[idx % 6]
        with col:
            st.markdown(f"""
            <div style="background:{sc['bg']};border:{border_style};border-radius:8px;
                 padding:8px 6px;text-align:center;cursor:pointer;margin-bottom:4px">
              <div style="font-size:20px;font-weight:800;color:{sc['color']}">{count}</div>
              <div style="font-size:9px;color:{sc['color']};font-weight:600;line-height:1.3">{sname}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("Filter", key=f"sf_{sname}", use_container_width=True):
                st.session_state["pi_status_filter"] = None if is_active else sname
                st.session_state["pi_expanded_feat"] = None
                st.rerun()

    st.markdown("---")

    # ── TEAM BOXES ──
    st.markdown('<div style="font-size:13px;font-weight:700;color:#1a202c;margin-bottom:10px">Team delivery</div>',
                unsafe_allow_html=True)
    team_cols = st.columns(5)
    for idx, team in enumerate(TEAMS):
        tc = TEAM_COLORS.get(team, "#6b7280")
        av = TEAM_AVATARS.get(team, "🔷")
        team_feats    = [f for f in features if f.get("scrum_team") == team]
        team_done     = sum(1 for f in team_feats if f["state"] in FEATURE_COMPLETED_STATES)
        team_total    = len(team_feats)
        pct           = round(team_done / team_total * 100) if team_total > 0 else 0
        is_active     = st.session_state["pi_team_filter"] == team
        border_top    = f"3px solid {tc}"
        border_others = f"2px solid {tc}" if is_active else "1px solid #e8ecf0"
        with team_cols[idx]:
            st.markdown(f"""
            <div style="background:#ffffff;border:{border_others};border-top:{border_top};
                 border-radius:8px;padding:10px 8px;text-align:center;margin-bottom:4px">
              <div style="font-size:16px">{av}</div>
              <div style="font-size:10px;font-weight:700;color:{tc};margin:3px 0;overflow:hidden;
                   text-overflow:ellipsis;white-space:nowrap">{team.split()[0]}</div>
              <div style="font-size:20px;font-weight:800;color:{tc}">{team_done}
                <span style="font-size:12px;color:#9ca3af">/{team_total}</span></div>
              <div style="font-size:9px;color:#9ca3af;margin-bottom:5px">features done</div>
              <div style="background:#f3f4f6;border-radius:3px;height:4px;overflow:hidden">
                <div style="width:{pct}%;height:100%;background:{tc};border-radius:3px"></div></div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"{team.split()[0]}", key=f"tf_{team}", use_container_width=True):
                st.session_state["pi_team_filter"] = None if is_active else team
                st.session_state["pi_expanded_feat"] = None
                st.rerun()

    st.markdown("---")

    # ── FILTER & SORT FEATURES ──
    sf = st.session_state["pi_status_filter"]
    tf = st.session_state["pi_team_filter"]
    sc_col = st.session_state["pi_sort_col"]
    sc_asc = st.session_state["pi_sort_asc"]

    filtered = features
    if sf:  filtered = [f for f in filtered if f["status"] == sf]
    if tf:  filtered = [f for f in filtered if f.get("scrum_team") == tf]

    # Add computed fields from task_data
    enriched = []
    for f in filtered:
        td   = task_data.get(f["id"], {})
        pdev = f.get("pdev", 0) or 0
        pqa  = f.get("pqa", 0) or 0
        adev = td.get("dev_actual", 0)
        aqa  = td.get("qa_actual", 0)
        enriched.append({**f,
            "dev_actual": adev, "qa_actual": aqa,
            "over_dev":   round(adev - pdev, 1),
            "over_qa":    round(aqa  - pqa, 1),
            "bug_count":  td.get("bug_count", 0),
            "tasks":      td.get("tasks", []),
            "is_overrun": (adev > pdev and pdev > 0) or (aqa > pqa and pqa > 0),
        })

    def sort_key(f):
        v = f.get(sc_col, 0) or 0
        return str(v).lower() if isinstance(v, str) else v
    enriched.sort(key=sort_key, reverse=not sc_asc)

    # ── TABS ──
    at_risk_feats  = [f for f in enriched if f["status"] in ["On Hold","Blocked by Dependent Bugs"] or f["is_overrun"]]
    overburn_feats = [f for f in enriched if f["is_overrun"]]
    blocked_feats  = [f for f in enriched if f["status"] in ["On Hold","Blocked by Dependent Bugs"]]

    tab_board, tab_risk, tab_over, tab_block, tab_bugs = st.tabs([
        f"📊 Feature board ({len(enriched)})",
        f"⚠️ At risk ({len(at_risk_feats)})",
        f"🔥 Overburn ({len(overburn_feats)})",
        f"🚧 Blocked ({len(blocked_feats)})",
        "🐛 Bug summary",
    ])

    def sort_header(label, col, current_col, current_asc):
        icon = "↑" if (current_col==col and current_asc) else "↓" if (current_col==col) else "↕"
        return f"{label} {icon}"

    def render_feature_table(feat_list, key_prefix):
        if not feat_list:
            st.success("✅ No items in this category")
            return

        # Active filter display + clear
        fc1, fc2 = st.columns([5,1])
        with fc1:
            tags = []
            if sf: tags.append(f"Status: {sf}")
            if tf: tags.append(f"Team: {tf}")
            tag_html = " &nbsp;·&nbsp; ".join(f'<span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;border-radius:20px;padding:1px 8px;font-size:11px">{t}</span>' for t in tags)
            st.markdown(f'<div style="font-size:12px;color:#6b7280;padding:4px 0">Showing {len(feat_list)} features {tag_html}</div>', unsafe_allow_html=True)
        with fc2:
            dl_buf = build_feature_excel(feat_list, task_data)
            st.download_button("📥 Export", data=dl_buf,
                               file_name=f"pi_{pi_name}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key=f"dl_{key_prefix}", use_container_width=True)

        # Column headers with sort buttons
        hcols = st.columns([3,5,12,8,7,7,5,5,5,5,5,5,4,4])
        headers = [
            ("PI #","pi_priority"),("ID","id"),("Title","title"),("Solution owner","solution_owner"),
            ("Scrum team","scrum_team"),("Dep. team","dep_team"),
            ("Plan dev","pdev"),("Act dev","dev_actual"),("Over dev","over_dev"),
            ("Plan QA","pqa"),("Act QA","qa_actual"),("Over QA","over_qa"),
            ("Bugs","bug_count"),("Link",""),
        ]
        for col_el, (lbl, col_key) in zip(hcols, headers):
            with col_el:
                if col_key:
                    arrow = "↑" if (sc_col==col_key and sc_asc) else "↓" if sc_col==col_key else ""
                    if st.button(f"{lbl}{' '+arrow if arrow else ''}", key=f"sh_{key_prefix}_{col_key}", use_container_width=True):
                        if st.session_state["pi_sort_col"] == col_key:
                            st.session_state["pi_sort_asc"] = not st.session_state["pi_sort_asc"]
                        else:
                            st.session_state["pi_sort_col"] = col_key
                            st.session_state["pi_sort_asc"] = True
                        st.rerun()
                else:
                    st.markdown(f'<div style="font-size:10px;color:#9ca3af;padding:5px 0">{lbl}</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:2px;background:#e8ecf0;margin-bottom:6px'></div>", unsafe_allow_html=True)

        for f in feat_list:
            odev = f["over_dev"]; oqa = f["over_qa"]
            is_or = f["is_overrun"]
            row_bg = "#fef2f2" if is_or else "#ffffff"
            odev_c = "#dc2626" if odev>0 else "#16a34a"
            oqa_c  = "#dc2626" if oqa>0 else "#16a34a"
            odev_t = f"+{odev}h" if odev>0 else "—"
            oqa_t  = f"+{oqa}h"  if oqa>0  else "—"

            # Status badge
            sc_info = PI_STATUS_COLORS.get(f["status"], {"bg":"#f9fafb","color":"#6b7280","border":"#e5e7eb"})

            rcols = st.columns([3,5,12,8,7,7,5,5,5,5,5,5,4,4])
            with rcols[0]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 4px;font-size:12px;font-weight:700;color:#374151;text-align:center;border-radius:4px">{f.get("pi_priority","—")}</div>',unsafe_allow_html=True)
            with rcols[1]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;color:#2563eb">{f["id"]}</div>',unsafe_allow_html=True)
            with rcols[2]:
                title_short = f["title"][:45]+"…" if len(f["title"])>45 else f["title"]
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:12px;font-weight:500" title="{f["title"]}">{title_short}<br><span style="font-size:10px;background:{sc_info["bg"]};color:{sc_info["color"]};border-radius:10px;padding:1px 6px">{f["status"]}</span></div>',unsafe_allow_html=True)
            with rcols[3]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;color:#374151">{f.get("solution_owner","—")[:18]}</div>',unsafe_allow_html=True)
            with rcols[4]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px">{str(f.get("scrum_team","—"))[:12]}</div>',unsafe_allow_html=True)
            with rcols[5]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;color:#6b7280">{str(f.get("dep_team","—"))[:12]}</div>',unsafe_allow_html=True)
            with rcols[6]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;text-align:center">{f.get("pdev",0) or 0}h</div>',unsafe_allow_html=True)
            with rcols[7]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;text-align:center">{f["dev_actual"]}h</div>',unsafe_allow_html=True)
            with rcols[8]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;text-align:center;color:{odev_c};font-weight:{"600" if odev>0 else "400"}">{odev_t}</div>',unsafe_allow_html=True)
            with rcols[9]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;text-align:center">{f.get("pqa",0) or 0}h</div>',unsafe_allow_html=True)
            with rcols[10]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;text-align:center">{f["qa_actual"]}h</div>',unsafe_allow_html=True)
            with rcols[11]:
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:11px;text-align:center;color:{oqa_c};font-weight:{"600" if oqa>0 else "400"}">{oqa_t}</div>',unsafe_allow_html=True)
            with rcols[12]:
                bc = f["bug_count"]
                bc_c = "#dc2626" if bc>0 else "#9ca3af"
                st.markdown(f'<div style="background:{row_bg};padding:6px 2px;font-size:12px;font-weight:700;color:{bc_c};text-align:center">{bc if bc>0 else "—"}</div>',unsafe_allow_html=True)
            with rcols[13]:
                st.link_button("↗", f.get("devops_url","#"), use_container_width=True)

            # Expand/collapse button
            exp_key  = f"exp_{key_prefix}_{f['id']}"
            is_exp   = st.session_state.get("pi_expanded_feat") == f"{key_prefix}_{f['id']}"
            exp_label= "▲ Hide tasks" if is_exp else "▼ Show tasks"
            if st.button(exp_label, key=exp_key, use_container_width=True):
                st.session_state["pi_expanded_feat"] = None if is_exp else f"{key_prefix}_{f['id']}"
                st.rerun()

            if is_exp:
                tasks = f.get("tasks", [])
                if not tasks:
                    st.info("No tasks/bugs found under this feature.")
                else:
                    # Download button
                    dl_t = build_task_excel(f, tasks)
                    dl_c1, dl_c2 = st.columns([6,1])
                    with dl_c1:
                        st.markdown(f'<div style="background:#f8fafc;border:1px solid #e8ecf0;border-radius:8px;padding:8px 12px;font-size:12px;font-weight:700">📋 Tasks &amp; bugs under {f["id"]} — {len(tasks)} items</div>',unsafe_allow_html=True)
                    with dl_c2:
                        st.download_button("📥", data=dl_t,
                                           file_name=f"tasks_{f['id']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                           key=f"tdl_{key_prefix}_{f['id']}", use_container_width=True)

                    th1,th2,th3,th4,th5,th6,th7,th8 = st.columns([5,14,8,6,5,5,5,5])
                    for th,lbl in zip([th1,th2,th3,th4,th5,th6,th7,th8],
                                      ["ID","Title","Assignee","State","Activity","Est","Done","Rem"]):
                        with th:
                            st.markdown(f'<div style="font-size:10px;color:#9ca3af;font-weight:600;padding:4px 2px">{lbl}</div>',unsafe_allow_html=True)

                    for t in tasks:
                        t_actual = t.get("done",0) + t.get("rem",0)
                        t_over   = t_actual > (t.get("est",0) or 0) and (t.get("est",0) or 0) > 0
                        t_act    = t.get("activity","")
                        is_excl  = t_act not in DEV_ACTIVITIES and t_act not in QA_ACTIVITIES and t.get("type")!="Bug"
                        t_bg     = "#fef2f2" if t_over else "#f8fafc"
                        tc1,tc2,tc3,tc4,tc5,tc6,tc7,tc8 = st.columns([5,14,8,6,5,5,5,5])
                        with tc1: st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:11px;color:#2563eb">{t["id"]}</div>',unsafe_allow_html=True)
                        with tc2: st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:11px;{"color:#9ca3af;" if is_excl else ""}" title="{t["title"]}">{t["title"][:40]}{"…" if len(t["title"])>40 else ""}</div>',unsafe_allow_html=True)
                        with tc3: st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:11px">{t["assignee"][:16]}</div>',unsafe_allow_html=True)
                        with tc4:
                            s_c = "#16a34a" if t["state"] in COMPLETED_STATES else "#2563eb" if t["state"]=="In Progress" else "#6b7280"
                            st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:11px;color:{s_c}">{t["state"]}</div>',unsafe_allow_html=True)
                        with tc5: st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:10px;color:#6b7280">{"(excl)" if is_excl else t_act[:8]}</div>',unsafe_allow_html=True)
                        with tc6: st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:11px;text-align:center">{t.get("est",0)}h</div>',unsafe_allow_html=True)
                        with tc7: st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:11px;text-align:center">{t.get("done",0)}h</div>',unsafe_allow_html=True)
                        with tc8: st.markdown(f'<div style="background:{t_bg};padding:4px 2px;font-size:11px;text-align:center;color:{"#d97706" if t.get("rem",0)>0 else "#9ca3af"}">{t.get("rem",0)}h</div>',unsafe_allow_html=True)

            st.markdown("<div style='height:1px;background:#f3f4f6'></div>", unsafe_allow_html=True)

    # ── RENDER EACH TAB ──
    with tab_board: render_feature_table(enriched,       "board")
    with tab_risk:  render_feature_table(at_risk_feats,  "risk")
    with tab_over:  render_feature_table(overburn_feats, "over")
    with tab_block: render_feature_table(blocked_feats,  "block")

    with tab_bugs:
        st.markdown('<div style="font-size:13px;font-weight:700;color:#1a202c;margin-bottom:10px">Bug summary by feature</div>',unsafe_allow_html=True)
        bug_rows = []
        for f in enriched:
            td  = task_data.get(f["id"], {})
            bc  = td.get("bug_count", 0)
            if bc == 0: continue
            tasks = td.get("tasks", [])
            bugs  = [t for t in tasks if t.get("type") == "Bug"]
            open_b   = sum(1 for b in bugs if b.get("state") not in COMPLETED_STATES)
            closed_b = sum(1 for b in bugs if b.get("state") in COMPLETED_STATES)
            bug_rows.append({
                "Feature ID":  f["id"],
                "Title":       f["title"][:50]+"…" if len(f["title"])>50 else f["title"],
                "Scrum Team":  f.get("scrum_team","—"),
                "Total Bugs":  bc,
                "Open":        open_b,
                "Closed":      closed_b,
                "DevOps URL":  f.get("devops_url",""),
            })
        if not bug_rows:
            st.success("✅ No bugs found under any feature.")
        else:
            st.dataframe(
                pd.DataFrame(bug_rows),
                use_container_width=True, hide_index=True, height=400,
                column_config={"DevOps URL": st.column_config.LinkColumn("DevOps", display_text="Open ↗")}
            )



# ─────────────────────────────────────────────────────────────────
# SPRINT MONITOR — ITEM TABLE
# ─────────────────────────────────────────────────────────────────
def items_to_df(items, sort_col=None, sort_asc=True):
    rows = []
    for i in items:
        sr = i.get("spill_risk","none"); ob = i.get("is_overburn",False)
        bk = i.get("is_blocked",False);  un = i.get("is_unestimated",False)
        di = i.get("has_date_issue",False)
        flags = ", ".join(filter(None,[
            "🔴 High Spill" if sr=="high" else "🟡 Watch" if sr=="watch" else "",
            "🔥 Overburn" if ob else "", "🚧 Blocked" if bk else "",
            "📋 No Est" if un else "", "📅 Date Issue" if di else ""])) or "✅ OK"
        rows.append({
            "ID": i.get("id"), "Type": i.get("type",""),
            "Title": (i["title"][:65]+"…") if len(i["title"])>65 else i["title"],
            "Assignee": i.get("assignee","—"), "State": i.get("state",""),
            "Est (h)": i.get("est") or 0, "Done (h)": i.get("done") or 0,
            "Rem (h)": i.get("rem") or 0, "Overrun (h)": i.get("overrun") or 0,
            "Spill Risk": sr.upper() if sr!="none" else "—",
            "Flags": flags, "Feature": i.get("feature_title","—"),
            "Tags": i.get("tags",""), "DevOps Link": i.get("devops_url",""),
        })
    df = pd.DataFrame(rows)
    if sort_col and sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=sort_asc)
    return df

def show_df(items, sort_col=None, asc=True, height=380, key=None):
    if not items:
        st.success("✅ No items in this category")
        return
    df = items_to_df(items, sort_col, asc)
    st.dataframe(df, use_container_width=True, hide_index=True, height=height, key=key,
                 column_config={"DevOps Link": st.column_config.LinkColumn("DevOps Link", display_text="Open ↗")})

# ─────────────────────────────────────────────────────────────────
# SPRINT MONITOR — TEAM CARD
# ─────────────────────────────────────────────────────────────────
def render_team_card(td, col):
    team = td.get("team",""); h = td.get("health","no_data"); s = STATUS[h]
    av = TEAM_AVATARS.get(team,"🔷"); tc = TEAM_COLORS.get(team,"#2563eb")
    hc = td.get("high_count",0); wc = td.get("watch_count",0)
    oc = td.get("over_count",0); bk = td.get("blocked_count",0)
    uc = td.get("unest_count",0); dc_ = td.get("date_issue_count",0)
    cp = td.get("comp_pct",0); dl = td.get("days_left",0)
    ss2 = td.get("sprint_start"); se2 = td.get("sprint_end"); tf = td.get("timeframe","current")
    date_tag = (f'<span style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;'
                f'border-radius:4px;padding:2px 7px;font-size:10px;font-weight:500;margin-left:6px">'
                f'{ss2.strftime("%b %d")} → {se2.strftime("%b %d")}</span>' if ss2 and se2 else "")
    past_tag = ('<span style="background:#fef3c7;color:#92400e;border-radius:4px;'
                'padding:2px 6px;font-size:10px;font-weight:700;margin-left:4px">LAST SPRINT</span>'
                if tf == "past" else "")
    dl_c = "#dc2626" if dl<=2 else "#d97706" if dl<=4 else "#6b7280"
    items = td.get("items",[])
    total_est  = sum(i.get("est",0) or 0 for i in items)
    total_done = sum(i.get("done",0) or 0 for i in items)

    with col:
        st.markdown(f"""
        <div style="background:#ffffff;border:1px solid #e8ecf0;border-top:3px solid {s['color']};
             border-radius:10px;padding:14px;margin-bottom:4px">
          <div style="margin-bottom:8px">
            <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:4px">
              <span style="font-size:17px">{av}</span>
              <span style="font-size:13px;font-weight:700;color:#1a202c">{team}</span>
              {date_tag}{past_tag}
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              {status_badge(h)}
              <span style="font-size:11px;color:{dl_c};font-weight:600">{dl}d left</span>
            </div>
          </div>
          <div style="font-size:10px;color:#9ca3af;font-weight:600;margin-bottom:3px">
            {cp}% COMPLETE &nbsp;·&nbsp; {total_done:.0f}h / {total_est:.0f}h estimated
          </div>
          {progress_bar(cp, s['color'])}
        </div>
        """, unsafe_allow_html=True)

        metrics = [
            ("🔴 High Spill", hc,  "#fef2f2", "#dc2626"),
            ("🟡 Watch",      wc,  "#fffbeb", "#d97706"),
            ("🔥 Overburn",   oc,  "#fff7ed", "#ea580c"),
            ("🚧 Blocked",    bk,  "#f5f3ff", "#7c3aed"),
            ("📋 No Est",     uc,  "#ecfeff", "#0891b2"),
            ("📅 Date Issue", dc_, "#fdf2f8", "#db2777"),
        ]
        # Row 1 — first 3 metrics
        r1 = st.columns(3)
        for idx in range(3):
            label, count, bg, color = metrics[idx]
            with r1[idx]:
                st.markdown(
                    f'<div style="background:{bg};border-radius:6px;padding:7px 4px;'
                    f'text-align:center;margin-bottom:3px">'
                    f'<div style="font-size:20px;font-weight:800;color:{color}">{count}</div>'
                    f'<div style="font-size:9px;color:#6b7280;font-weight:600">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True)
        # Row 2 — last 3 metrics
        r2 = st.columns(3)
        for idx in range(3, 6):
            label, count, bg, color = metrics[idx]
            with r2[idx - 3]:
                st.markdown(
                    f'<div style="background:{bg};border-radius:6px;padding:7px 4px;'
                    f'text-align:center;margin-bottom:3px">'
                    f'<div style="font-size:20px;font-weight:800;color:{color}">{count}</div>'
                    f'<div style="font-size:9px;color:#6b7280;font-weight:600">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True)

        # Single row of action buttons — stable, no per-metric columns
        btn_cols = st.columns(3)
        with btn_cols[0]:
            if hc > 0 or wc > 0:
                if st.button("⚠️ Spill", key=f"card_{team}_spill", use_container_width=True):
                    f = "high_spill" if hc > 0 else "watch"
                    if st.session_state.get(f"card_filter_{team}") != f or st.session_state.get("view") != "team_detail":
                        st.session_state[f"card_filter_{team}"] = f
                        st.session_state.update({"view":"team_detail","selected_team":team})
                        st.rerun()
        with btn_cols[1]:
            if oc > 0:
                if st.button("🔥 Burn", key=f"card_{team}_over", use_container_width=True):
                    if st.session_state.get(f"card_filter_{team}") != "overburn" or st.session_state.get("view") != "team_detail":
                        st.session_state[f"card_filter_{team}"] = "overburn"
                        st.session_state.update({"view":"team_detail","selected_team":team})
                        st.rerun()
        with btn_cols[2]:
            if st.button("Full →", key=f"full_{team}", use_container_width=True):
                if st.session_state.get("selected_team") != team or st.session_state.get("view") != "team_detail":
                    st.session_state[f"card_filter_{team}"] = None
                    st.session_state.update({"view":"team_detail","selected_team":team})
                    st.rerun()

# ─────────────────────────────────────────────────────────────────
# SPRINT MONITOR — NINE BOX
# ─────────────────────────────────────────────────────────────────
def render_nine_box(all_data):
    import plotly.graph_objects as go
    members = defaultdict(lambda: {"items":[],"team":""})
    for t in all_data:
        for i in t.get("items",[]):
            a = i.get("assignee","Unassigned")
            members[a]["items"].append(i); members[a]["team"] = t.get("team","")
    dots = []
    for name, data in members.items():
        items = data["items"]; team = data["team"]
        if not items: continue
        comp = hour_completion_pct(items); rsc = member_risk_score(items)
        est_h = sum(i.get("est",0) or 0 for i in items)
        sh = sum(1 for i in items if i.get("spill_risk")=="high")
        sw = sum(1 for i in items if i.get("spill_risk")=="watch")
        oc = sum(1 for i in items if i.get("is_overburn"))
        bc = sum(1 for i in items if i.get("is_blocked"))
        total = len(items); risk_n = min(rsc*5,100); dot_sz = max(24,min(est_h*1.5,46))
        if sh>0: dc="#dc2626"
        elif oc>0: dc="#ea580c"
        elif bc>0: dc="#7c3aed"
        elif sw>0: dc="#ca8a04"
        else: dc="#16a34a"
        in_crit = risk_n>60 and comp<40
        dots.append({"name":name,"team":team,"x":comp,"y":risk_n,"sz":dot_sz,"dc":dc,
                     "label":name.split()[0] if in_crit else inits(name),"crit":in_crit,
                     "comp":comp,"rsc":rsc,"sh":sh,"sw":sw,"oc":oc,"bc":bc,
                     "total":total,"est_h":est_h,"has_b":bc>0})
    if not dots: st.info("No member data."); return
    fig = go.Figure()
    quads = [
        (0,66,40,100,"#fef2f2","🔴  CRITICAL","#dc2626"),
        (40,66,75,100,"#fff7ed","🔥  OVERLOADED","#ea580c"),
        (75,66,100,100,"#fefce8","⚡  STRETCHED","#ca8a04"),
        (0,33,40,66,"#fff7ed","⚠️  STRUGGLING","#ea580c"),
        (40,33,75,66,"#fefce8","👁  WATCH","#ca8a04"),
        (75,33,100,66,"#f0fdf4","📈  ON TRACK","#16a34a"),
        (0,0,40,33,"#fefce8","🐢  SLOW START","#ca8a04"),
        (40,0,75,33,"#f0fdf4","✅  DELIVERING","#16a34a"),
        (75,0,100,33,"#f0fdf4","⭐  STAR","#16a34a"),
    ]
    for x0,y0,x1,y1,bg,lbl,lc in quads:
        fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,fillcolor=bg,line=dict(color="#e5e7eb",width=1.5))
        fig.add_annotation(x=(x0+x1)/2,y=(y0+y1)/2+14,text=f"<b>{lbl}</b>",
                           font=dict(size=10,color=lc),showarrow=False,xanchor="center",yanchor="middle")
    for v in [40,75]:
        fig.add_shape(type="line",x0=v,y0=0,x1=v,y1=100,line=dict(color="#d1d5db",width=1.5,dash="dash"))
    for h2 in [33,66]:
        fig.add_shape(type="line",x0=0,y0=h2,x1=100,y1=h2,line=dict(color="#d1d5db",width=1.5,dash="dash"))
    for d in [x for x in dots if x["has_b"]]:
        fig.add_trace(go.Scatter(x=[d["x"]],y=[d["y"]],mode="markers",
            marker=dict(size=d["sz"]+14,color="rgba(124,58,237,0.12)",line=dict(color="#7c3aed",width=2.5)),
            showlegend=False,hoverinfo="skip"))
    for d in dots:
        tc = TEAM_COLORS.get(d["team"],"#6b7280")
        fig.add_trace(go.Scatter(x=[d["x"]],y=[d["y"]],mode="markers+text",
            marker=dict(size=d["sz"],color=d["dc"],opacity=0.9,line=dict(color="rgba(255,255,255,0.8)",width=2)),
            text=f"<b>{d['label']}</b>",textposition="middle center",textfont=dict(size=9,color="#ffffff"),
            customdata=[[d["name"],d["team"],d["comp"],d["rsc"],d["sh"],d["sw"],d["oc"],d["bc"],d["total"],d["est_h"]]],
            hovertemplate=("<b>%{customdata[0]}</b><br>Team: %{customdata[1]}<br>"
                          "Completion: %{customdata[2]}%<br>Risk Score: %{customdata[3]}<br>"
                          "🔴 High: %{customdata[4]} · 🟡 Watch: %{customdata[5]}<br>"
                          "🔥 Overburn: %{customdata[6]} · 🚧 Blocked: %{customdata[7]}<br>"
                          "Items: %{customdata[8]} · Est: %{customdata[9]:.0f}h<extra></extra>"),
            showlegend=False,name=d["name"]))
    fig.update_layout(height=500,margin=dict(l=60,r=20,t=40,b=60),
        plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
        title_text="<b>Member Performance Nine-Box</b>",title_x=0.0,
        clickmode="event+select",
        xaxis=dict(range=[-8,108],showgrid=False,zeroline=False,showticklabels=False,title=""),
        yaxis=dict(range=[-12,108],showgrid=False,zeroline=False,showticklabels=False,title=""))
    event = st.plotly_chart(fig,use_container_width=True,on_select="rerun",key="nine_box")
    if event and event.get("selection") and event["selection"].get("points"):
        pts = event["selection"]["points"]
        if pts:
            clicked_name = pts[0].get("customdata",[None])[0]
            if clicked_name:
                all_items = [i for t in all_data for i in t.get("items",[])]
                member_items = [i for i in all_items if i.get("assignee")==clicked_name]
                if member_items:
                    team_name = member_items[0].get("team",""); tc2 = TEAM_COLORS.get(team_name,"#2563eb")
                    st.markdown(
                        f'<div style="margin-top:12px;padding:10px 16px;background:#f8fafc;'
                        f'border-left:4px solid {tc2};border-radius:0 8px 8px 0;display:flex;align-items:center;gap:10px">'
                        f'<span style="font-size:15px;font-weight:700">{clicked_name}</span>'
                        f'<span style="font-size:12px;color:#6b7280">{team_name} · {len(member_items)} items</span>'
                        f'</div>',unsafe_allow_html=True)
                    risk_order = {"high":0,"watch":1,"none":2}
                    member_items.sort(key=lambda x:risk_order.get(x.get("spill_risk","none"),2))
                    show_df(member_items,"Spill Risk",height=280,key=f"nb_{clicked_name}")


# ─────────────────────────────────────────────────────────────────
# SPRINT MONITOR — MAIN VIEW
# ─────────────────────────────────────────────────────────────────
def render_sprint_monitor(all_data):
    all_items   = [i for t in all_data for i in t.get("items",[])]
    spill_high  = [i for i in all_items if i.get("spill_risk")=="high"]
    spill_watch = [i for i in all_items if i.get("spill_risk")=="watch"]
    overs       = [i for i in all_items if i.get("is_overburn")]
    blocked_all = [i for i in all_items if i.get("is_blocked")]
    unest_all   = [i for i in all_items if i.get("is_unestimated")]
    date_all    = [i for i in all_items if i.get("has_date_issue")]
    both        = [i for i in all_items if i.get("spill_risk") in ["high","watch"] and i.get("is_overburn")]
    total_est   = sum(i.get("est",0) or 0 for i in all_items)
    total_done  = sum(i.get("done",0) or 0 for i in all_items)
    comp_pct    = min(round(total_done/total_est*100),100) if total_est>0 else 0
    total_ov    = sum(i.get("overrun",0) for i in overs)
    now         = datetime.now().strftime("%d %b %Y  %H:%M")
    active      = [t for t in all_data if t.get("sprint_end")]
    ends        = [t["sprint_end"] for t in active]
    earliest    = min(ends) if ends else None; latest = max(ends) if ends else None
    all_same    = (earliest==latest) if ends else True
    min_dl      = min((t.get("days_left",0) for t in active),default=0)
    max_dl      = max((t.get("days_left",0) for t in active),default=0)
    if all_same and earliest:
        date_str = f"{earliest.strftime('%d %b %Y')}"; days_str = f"{min_dl} working days left"
    else:
        date_str = f"{earliest.strftime('%d %b') if earliest else '—'} – {latest.strftime('%d %b %Y') if latest else '—'}"
        days_str = f"{min_dl}–{max_dl} days left (varies by team)"
    overall = "healthy"
    for t in all_data:
        h2 = t.get("health","no_data")
        if h2=="critical": overall="critical"; break
        if h2=="atrisk" and overall!="critical": overall="atrisk"
        if h2=="watch" and overall not in ["critical","atrisk"]: overall="watch"
    os_ = STATUS[overall]
    past_teams = [t["team"] for t in all_data if t.get("timeframe")=="past"]

    # Header
    st.markdown(f"""
    <div style="background:#ffffff;border-bottom:1px solid #e8ecf0;padding:14px 24px;
         display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:8px">
      <div>
        <div style="font-size:20px;font-weight:800;color:#1a202c">Sprint Execution Monitor</div>
        <div style="font-size:12px;color:#6b7280;margin-top:3px">
          5 Teams &nbsp;·&nbsp; HRM Project &nbsp;·&nbsp;
          <span style="color:#374151;font-weight:500">{date_str}</span> &nbsp;·&nbsp;
          <span style="color:{'#dc2626' if min_dl<=2 else '#d97706' if min_dl<=4 else '#374151'};font-weight:600">{days_str}</span>
          {(" · <span style='color:#92400e'>📅 "+", ".join(past_teams)+" on last sprint</span>") if past_teams else ""}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span style="background:{os_['bg']};color:{os_['color']};border:1px solid {os_['border']};
          border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700">{os_['icon']} {os_['text'].upper()}</span>
        <span style="font-size:12px;color:#9ca3af">{comp_pct}% · {total_done:.0f}/{total_est:.0f}h</span>
        <span style="font-size:11px;color:#9ca3af">{now}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Nine-box toggle
    nb_col, _ = st.columns([1,5])
    with nb_col:
        if st.button("🔲 Nine-Box Grid", key="toggle_nine_box", use_container_width=True):
            st.session_state["show_nine_box"] = not st.session_state.get("show_nine_box",False)
            st.rerun()

    # Metrics
    env_c = sum(1 for i in blocked_all if any(t=="Env-Unstable" for t,_ in i.get("blocked_tags",[])))
    pr_c  = sum(1 for i in blocked_all if any(t=="PR-Approval" for t,_ in i.get("blocked_tags",[])))
    td_c  = sum(1 for i in blocked_all if any(t=="Test-Data-Issue" for t,_ in i.get("blocked_tags",[])))
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    with m1: st.metric("⚠️ Potential Spillover",  len(spill_high)+len(spill_watch), f"{len(spill_high)} High · {len(spill_watch)} Watch")
    with m2: st.metric("🔥 Overburn Items",        len(overs),                       f"+{total_ov:.0f}h total overrun")
    with m3: st.metric("🚧 Externally Blocked",    len(blocked_all),                 f"🌩️{env_c} 🔀{pr_c} 🗄️{td_c}")
    with m4: st.metric("📋 No Estimate",           len(unest_all),                   "items without effort")
    with m5: st.metric("📅 Date Issues",           len(date_all),                    "missing or out of range")
    with m6: st.metric("✅ Completion",             f"{comp_pct}%",                  f"{total_done:.0f}h of {total_est:.0f}h")

    st.markdown("---", unsafe_allow_html=True)

    # Nine-box
    if st.session_state.get("show_nine_box",False):
        render_nine_box(all_data)
        st.markdown("---", unsafe_allow_html=True)

    # Team cards
    st.markdown('<div style="font-size:14px;font-weight:700;color:#1a202c;margin-bottom:12px">Team Sprint Status</div>',
                unsafe_allow_html=True)
    order = {"critical":0,"atrisk":1,"watch":2,"healthy":3,"no_data":4}
    sorted_d = sorted(all_data, key=lambda x:order.get(x.get("health","no_data"),4))
    tcols = st.columns(5)
    for col, td in zip(tcols, sorted_d):
        render_team_card(td, col)

    st.markdown("---", unsafe_allow_html=True)

    # Items table
    ct, cd = st.columns([5,1])
    with ct:
        st.markdown('<div style="font-size:14px;font-weight:700;color:#1a202c;margin-bottom:4px">Items Going Out of Track</div>',
                    unsafe_allow_html=True)
    with cd:
        buf = build_excel(all_data)
        st.download_button("📥 Excel", data=buf,
                           file_name=f"sprint_all_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_all", use_container_width=True)

    tabs = st.tabs([
        f"⚠️ Spillover ({len(spill_high)+len(spill_watch)})",
        f"🔥 Overburn ({len(overs)})",
        f"🚧 Blocked ({len(blocked_all)})",
        f"📋 No Estimate ({len(unest_all)})",
        f"📅 Date Issues ({len(date_all)})",
        f"💀 Both Issues ({len(both)})",
    ])
    with tabs[0]: show_df(sorted(spill_high+spill_watch,key=lambda x:0 if x.get("spill_risk")=="high" else 1),"Spill Risk",key="t0")
    with tabs[1]: show_df(sorted(overs,key=lambda x:x.get("overrun",0),reverse=True),"Overrun (h)",asc=False,key="t1")
    with tabs[2]:
        if not blocked_all: st.success("✅ No externally blocked items")
        else:
            grouped = defaultdict(list)
            for item in blocked_all:
                for tag,cfg2 in item.get("blocked_tags",[]): grouped[tag].append(item)
            for tag, items2 in grouped.items():
                tc2 = BLOCKED_TAGS.get(tag,BLOCKED_TAGS["Blocked"])
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:#f8fafc;border-left:4px solid {tc2["color"]};margin-bottom:6px"><span style="font-size:16px">{tc2["icon"]}</span><div><b style="color:{tc2["color"]}">{tc2["label"]}</b> <span style="color:#6b7280">· {len(items2)} items · Escalate: <b>{tc2["owner"]}</b></span></div></div>',unsafe_allow_html=True)
                show_df(items2,"Rem (h)",asc=False,height=240,key=f"t2_{tag}")
    with tabs[3]: show_df(unest_all,"State",key="t3")
    with tabs[4]:
        if not date_all: st.success("✅ No date issues")
        else:
            rows2=[{"ID":i.get("id"),"Title":(i["title"][:58]+"…") if len(i["title"])>58 else i["title"],
                    "Assignee":i.get("assignee",""),"State":i.get("state",""),"Team":i.get("team",""),
                    "Issue":" | ".join(i.get("date_violations",[])),
                    "Item Start":str(i.get("item_start","")) or "NOT SET",
                    "Item Target":str(i.get("item_target","")) or "NOT SET",
                    "Sprint Start":str(i.get("sprint_start","")),"Sprint End":str(i.get("sprint_end","")),
                    "DevOps Link":i.get("devops_url","")} for i in date_all]
            st.dataframe(pd.DataFrame(rows2),use_container_width=True,hide_index=True,height=400,
                         column_config={"DevOps Link":st.column_config.LinkColumn("DevOps Link",display_text="Open ↗")})
    with tabs[5]: show_df(sorted(both,key=lambda x:x.get("overrun",0),reverse=True),"Overrun (h)",asc=False,key="t5")

# ─────────────────────────────────────────────────────────────────
# SPRINT MONITOR — TEAM DETAIL VIEW
# ─────────────────────────────────────────────────────────────────
def render_members(items):
    mems = defaultdict(lambda:{"items":[],"done":0,"spill":0,"over":0,"block":0,"logged":0,"est":0})
    for item in items:
        a = item.get("assignee","Unassigned"); mems[a]["items"].append(item)
        if item["state"] in COMPLETED:                     mems[a]["done"] +=1
        if item.get("spill_risk") in ["high","watch"]:     mems[a]["spill"]+=1
        if item.get("is_overburn"):                        mems[a]["over"] +=1
        if item.get("is_blocked"):                         mems[a]["block"]+=1
        mems[a]["logged"] += item.get("done",0) or 0
        mems[a]["est"]    += item.get("est",0)  or 0
    sorted_m = sorted(mems.items(),key=lambda x:x[1]["spill"]*3+x[1]["over"]*2+x[1]["block"],reverse=True)
    cols = st.columns(min(len(sorted_m),4))
    for idx,(name,data) in enumerate(sorted_m):
        col = cols[idx%4]; total = len(data["items"])
        pct = min(round(data["logged"]/data["est"]*100),100) if data["est"]>0 else 0
        bar_c = "#16a34a" if pct>=80 else "#d97706" if pct>=50 else "#dc2626"
        has_spill = data["spill"]>0; has_block = data["block"]>0
        border_c = "#dc2626" if has_spill else "#7c3aed" if has_block else "#e8ecf0"
        bg_av = "#fef2f2" if has_spill else "#f5f3ff" if has_block else "#f1f5f9"
        txt_av = "#dc2626" if has_spill else "#7c3aed" if has_block else "#6b7280"
        with col:
            st.markdown(f"""
            <div style="background:#ffffff;border:2px solid {border_c};border-radius:10px;padding:14px;margin-bottom:10px">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
                <div style="width:34px;height:34px;border-radius:50%;background:{bg_av};border:2px solid {border_c};
                     display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:{txt_av}">{inits(name)}</div>
                <div>
                  <div style="font-size:13px;font-weight:700;color:#1a202c">{name}</div>
                  <div style="font-size:11px;color:#9ca3af">{total} items · {data['logged']:.0f}h logged</div>
                </div>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:5px;margin-bottom:8px;text-align:center">
                <div style="background:#f0fdf4;border-radius:5px;padding:5px"><div style="font-size:16px;font-weight:800;color:#16a34a">{data['done']}</div><div style="font-size:9px;color:#6b7280">DONE</div></div>
                <div style="background:#fef2f2;border-radius:5px;padding:5px"><div style="font-size:16px;font-weight:800;color:#dc2626">{data['spill']}</div><div style="font-size:9px;color:#6b7280">SPILL</div></div>
                <div style="background:#fff7ed;border-radius:5px;padding:5px"><div style="font-size:16px;font-weight:800;color:#ea580c">{data['over']}</div><div style="font-size:9px;color:#6b7280">OVER</div></div>
                <div style="background:#f5f3ff;border-radius:5px;padding:5px"><div style="font-size:16px;font-weight:800;color:#7c3aed">{data['block']}</div><div style="font-size:9px;color:#6b7280">BLOCK</div></div>
              </div>
              <div style="font-size:10px;color:#9ca3af;font-weight:600;margin-bottom:3px">{pct}% · {data['est']:.0f}h est</div>
              {progress_bar(pct, bar_c, 4)}
            </div>""", unsafe_allow_html=True)

def render_team_detail(tdata, all_data):
    team = tdata.get("team",""); health = tdata.get("health","no_data"); s = STATUS[health]
    items = tdata.get("items",[]); av = TEAM_AVATARS.get(team,"🔷")
    dl = tdata.get("days_left",0); ss = tdata.get("sprint_start"); se = tdata.get("sprint_end")
    sn = tdata.get("sprint_name","—"); tf = tdata.get("timeframe","current")
    dl_c = "#dc2626" if dl<=2 else "#d97706" if dl<=4 else "#374151"
    date_rng = f"{ss.strftime('%d %b') if ss else '—'} → {se.strftime('%d %b %Y') if se else '—'}"
    card_filter = st.session_state.get(f"card_filter_{team}")

    cb, ch = st.columns([1,10])
    with cb:
        if st.button("← Back"):
            st.session_state[f"card_filter_{team}"] = None
            st.session_state["view"] = "alert_center"; st.rerun()
    with ch:
        past_b = (' <span style="background:#fef3c7;color:#92400e;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:700">LAST SPRINT</span>' if tf=="past" else "")
        st.markdown(f"""
        <div style="padding:4px 0">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <span style="font-size:22px">{av}</span>
            <span style="font-size:20px;font-weight:800;color:#1a202c">{team}</span>
            {status_badge(health)}{past_b}
          </div>
          <div style="font-size:13px;color:#6b7280;margin-top:4px">
            {sn} &nbsp;·&nbsp;
            <span style="background:#f1f5f9;color:#374151;border-radius:4px;padding:2px 8px;font-size:12px">{date_rng}</span>
            &nbsp;·&nbsp; <span style="color:{dl_c};font-weight:600">{dl} working days left</span>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    spill_h = [i for i in items if i.get("spill_risk")=="high"]
    spill_w = [i for i in items if i.get("spill_risk")=="watch"]
    overs   = [i for i in items if i.get("is_overburn")]
    blocked = [i for i in items if i.get("is_blocked")]
    done_it = [i for i in items if i["state"] in COMPLETED]
    unest   = [i for i in items if i.get("is_unestimated")]
    datei   = [i for i in items if i.get("has_date_issue")]
    total_est  = sum(i.get("est",0) or 0 for i in items)
    total_done = sum(i.get("done",0) or 0 for i in items)
    total_rem  = sum(i.get("rem",0) or 0 for i in items)
    cp = hour_completion_pct(items)

    k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
    with k1: st.metric("Total Items", len(items), f"{len(done_it)} done")
    with k2: st.metric("🔴 High Spill", len(spill_h), "likely to spill")
    with k3: st.metric("🟡 Watch", len(spill_w), "needs attention")
    with k4: st.metric("🔥 Overburn", len(overs), f"+{sum(i.get('overrun',0) for i in overs):.0f}h")
    with k5: st.metric("🚧 Blocked", len(blocked), "external dependency")
    with k6: st.metric("📋 No Estimate", len(unest), "missing effort")
    with k7: st.metric("📅 Date Issues", len(datei), "fix before sprint")

    # Hours bar
    dcol, excol = st.columns([5,1])
    with dcol:
        st.markdown(f"""
        <div style="background:#f8fafc;border:1px solid #e8ecf0;border-radius:8px;padding:10px 18px;
             margin:10px 0;display:flex;gap:28px;align-items:center;flex-wrap:wrap">
          <div><span style="font-size:11px;color:#9ca3af;font-weight:600">ESTIMATED </span>
               <span style="font-size:15px;font-weight:800;color:#1a202c">{total_est:.0f}h</span></div>
          <div><span style="font-size:11px;color:#9ca3af;font-weight:600">LOGGED </span>
               <span style="font-size:15px;font-weight:800;color:#16a34a">{total_done:.0f}h</span></div>
          <div><span style="font-size:11px;color:#9ca3af;font-weight:600">REMAINING </span>
               <span style="font-size:15px;font-weight:800;color:#d97706">{total_rem:.0f}h</span></div>
          <div><span style="font-size:11px;color:#9ca3af;font-weight:600">COMPLETION </span>
               <span style="font-size:15px;font-weight:800;color:#2563eb">{cp}%</span>
               <span style="font-size:10px;color:#9ca3af"> (hours-based)</span></div>
        </div>""", unsafe_allow_html=True)
    with excol:
        buf = build_excel([tdata])
        st.download_button("📥 Excel", data=buf,
                           file_name=f"sprint_{team.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_t", use_container_width=True)

    if card_filter:
        filter_map = {"high_spill":spill_h,"watch":spill_w,"overburn":overs,
                      "blocked":blocked,"unestimated":unest,"date_issue":datei}
        label_map  = {"high_spill":"🔴 High Spill Risk","watch":"🟡 Watch Items",
                      "overburn":"🔥 Overburn Items","blocked":"🚧 Blocked Items",
                      "unestimated":"📋 Items Without Estimate","date_issue":"📅 Date Issues"}
        st.markdown(f'<div style="font-size:14px;font-weight:700;color:#1a202c;margin-bottom:8px">{label_map.get(card_filter,"")}</div>',unsafe_allow_html=True)
        show_df(filter_map.get(card_filter,[]),height=340,key=f"card_view_{card_filter}")
        st.markdown("---")
        if st.button("← Show all tabs"):
            st.session_state[f"card_filter_{team}"] = None; st.rerun()
        return

    tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs([
        f"⚠️ Spillover ({len(spill_h)+len(spill_w)})",
        f"🔥 Overburn ({len(overs)})",
        f"🚧 Blocked ({len(blocked)})",
        f"⚠️ Data Quality ({len(unest)+len(datei)})",
        f"👥 Members",
        f"📋 All Items ({len(items)})",
    ])
    with tab1: show_df(sorted(spill_h+spill_w,key=lambda x:0 if x.get("spill_risk")=="high" else 1),"Spill Risk",key="td1")
    with tab2: show_df(sorted(overs,key=lambda x:x.get("overrun",0),reverse=True),"Overrun (h)",asc=False,key="td2")
    with tab3:
        if not blocked: st.success("✅ No blocked items")
        else:
            grouped = defaultdict(list)
            for item in blocked:
                for tag,_ in item.get("blocked_tags",[]): grouped[tag].append(item)
            for tag,its in grouped.items():
                tc2 = BLOCKED_TAGS.get(tag,BLOCKED_TAGS["Blocked"])
                st.markdown(f'<div style="padding:7px 12px;background:#f8fafc;border-left:4px solid {tc2["color"]};margin-bottom:6px"><b style="color:{tc2["color"]}">{tc2["icon"]} {tc2["label"]}</b> <span style="color:#6b7280">· Escalate to: <b>{tc2["owner"]}</b></span></div>',unsafe_allow_html=True)
                show_df(its,"Rem (h)",asc=False,height=200,key=f"td3_{tag}")
    with tab4:
        if not unest and not datei: st.success("✅ No data quality issues")
        else:
            if unest:
                st.markdown('<div style="font-size:13px;font-weight:600;color:#0891b2;margin-bottom:6px">📋 Items Without Original Estimate</div>',unsafe_allow_html=True)
                show_df(unest,"State",height=260,key="td4a")
            if datei:
                st.markdown('<div style="font-size:13px;font-weight:600;color:#db2777;margin:10px 0 6px">📅 Items With Date Issues</div>',unsafe_allow_html=True)
                rows2=[{"ID":i.get("id"),"Title":(i["title"][:52]+"…") if len(i["title"])>52 else i["title"],
                        "Assignee":i.get("assignee",""),"State":i.get("state",""),
                        "Issue":" | ".join(i.get("date_violations",[])),
                        "Item Start":str(i.get("item_start","")) or "NOT SET",
                        "Item Target":str(i.get("item_target","")) or "NOT SET",
                        "DevOps Link":i.get("devops_url","")} for i in datei]
                st.dataframe(pd.DataFrame(rows2),use_container_width=True,hide_index=True,height=260,
                             column_config={"DevOps Link":st.column_config.LinkColumn("DevOps Link",display_text="Open ↗")})
    with tab5: render_members(items)
    with tab6: show_df(items,"Flags",height=440,key="td6")


# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown('<div style="font-size:16px;font-weight:800;color:#1a202c;padding:8px 0 16px">⚙️ Connection</div>',
                    unsafe_allow_html=True)
        has_secret = bool(st.session_state.get("pat") and "YOUR_ORG" not in st.session_state.get("org_url",""))
        if has_secret:
            st.success("✅ Connected via Streamlit Secrets")
            org_short = st.session_state.get("org_url","").split("/")[-1]
            st.markdown(f'<div style="font-size:12px;color:#6b7280">Org: <b>{org_short}</b><br>Project: <b>{st.session_state.get("project","")}</b></div>',
                        unsafe_allow_html=True)
        else:
            org  = st.text_input("Organisation URL", value=st.session_state.get("org_url","https://dev.azure.com/YOUR_ORG"))
            proj = st.text_input("Project Name",     value=st.session_state.get("project","HRM"))
            pat  = st.text_input("Personal Access Token", value=st.session_state.get("pat",""), type="password")
            if st.button("🔄 Load Live", use_container_width=True):
                if org and proj and pat:
                    st.session_state.update({"org_url":org,"project":proj,"pat":pat,"use_demo":False,"loaded":False})
                    st.cache_data.clear(); st.rerun()
                else:
                    st.error("Fill all fields")

        st.markdown("---")

        # PI selector
        st.markdown('<div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:6px">PI Selection</div>',
                    unsafe_allow_html=True)
        pi_name = st.text_input("Current PI", value=st.session_state.get("current_pi","26R1"))
        if pi_name != st.session_state.get("current_pi","26R1"):
            st.session_state["current_pi"] = pi_name
            st.session_state["pi_loaded"] = False
            st.cache_data.clear(); st.rerun()

        st.markdown("---")
        if st.button("🧪 Demo Data", use_container_width=True):
            st.session_state.update({"use_demo":True,"loaded":False,"pi_loaded":False}); st.rerun()
        if st.session_state.get("loaded"):
            if st.button("🔃 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.session_state.update({"loaded":False,"pi_loaded":False,"pi_insights":None})
                st.rerun()
        st.markdown("---")
        st.markdown("""<div style="font-size:12px;color:#6b7280;line-height:2">
<b style="color:#374151">PAT needs:</b><br>
· Work Items → Read<br>· Project & Team → Read<br>· Comments → Read<br>
<br><b style="color:#374151">Auto-refreshes every 5 min</b><br>
<br><b style="color:#374151">Sri Lanka holidays</b><br>2025–2026 included</div>""", unsafe_allow_html=True)
        st.markdown("---")
        with st.expander("🔍 PI field name not loading?"):
            st.markdown("""<div style="font-size:11px;color:#374151;line-height:1.8">
If features show 0, your Azure DevOps PI field name may differ.<br><br>
<b>To find it:</b><br>
1. Open any Feature in DevOps<br>
2. Paste this in browser:<br>
<code>https://dev.azure.com/PeoplesHR/HRM/_apis/wit/workitems/133815?$expand=all&api-version=7.0</code><br>
3. Press Ctrl+F, search "26R1"<br>
4. Note the field key above it
</div>""", unsafe_allow_html=True)
            custom_field = st.text_input("Override PI field name", value="Custom.PI", key="pi_field_override")
            if st.button("Apply field name", key="apply_field"):
                st.session_state["pi_field_name"] = custom_field
                st.session_state["pi_loaded"] = False
                st.cache_data.clear(); st.rerun()

        with st.expander("🩺 Debug PI loading"):
            if st.button("Run diagnostic", key="diag_btn"):
                org = st.session_state.get("org_url","")
                pat = st.session_state.get("pat","")
                pi  = st.session_state.get("current_pi","26R1")
                if pat and "YOUR_ORG" not in org:
                    cl = DevOpsClient(org, pat)
                    st.write(f"**Org:** {org} | **PI:** {pi}")

                    # Test 1: Epic by title
                    epic_ids = cl.get_pi_epics("HRM", pi)
                    st.write(f"**Epic IDs:** {epic_ids}")
                    err = st.session_state.get("_wiql_last_error","")
                    if err: st.error(f"Last WIQL error: {err}")

                    # Test 2: Features via Custom.PI
                    q = f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = 'HRM' AND [System.WorkItemType] = 'Feature' AND [Custom.PI] = '{pi}'"
                    ids = cl._wiql("HRM", q)
                    st.write(f"**Features via Custom.PI:** {len(ids)}")
                    err2 = st.session_state.get("_wiql_last_error","")
                    if err2: st.error(f"Feature query error: {err2}")

                    # Test 3: if Custom.PI fails, try without field filter to count features
                    if not ids:
                        q2 = f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = 'HRM' AND [System.WorkItemType] = 'Feature' AND [System.Tags] CONTAINS '{pi}'"
                        ids2 = cl._wiql("HRM", q2)
                        st.write(f"**Features via Tags contains {pi}:** {len(ids2)}")

                    # Show sample feature fields if found
                    sample_ids = ids or []
                    if sample_ids:
                        sample = cl.get_wi_batch(sample_ids[:1], [
                            "System.Id","System.Title","System.State",
                            "Custom.PI","Custom.ScrumTeamOwnership",
                            "Custom.PlannedDevEffort","Custom.PlannedQAEffort"
                        ])
                        if sample:
                            st.write("**Sample feature fields:**")
                            st.json(sample[0].get("fields",{}))
                else:
                    st.warning("Connect to Azure DevOps first")

# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    defaults = {
        "view": "alert_center", "selected_team": TEAMS[0],
        "use_demo": False, "loaded": False, "pi_loaded": False,
        "all_data": [], "pi_data": {},
        "show_connect": False, "show_nine_box": False,
        "org_url": "https://dev.azure.com/YOUR_ORG", "project": "HRM", "pat": "",
        "current_pi": "26R1",
        "pm_actions": [],
        "active_tab": "pi",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    render_sidebar()

    # Auto-load from secrets
    if st.session_state.get("pat") and "YOUR_ORG" not in st.session_state.get("org_url",""):
        if not st.session_state.get("loaded"):
            st.session_state["use_demo"] = False

    # ── DATA LOADING ──
    if not st.session_state["loaded"]:
        if st.session_state.get("use_demo"):
            with st.spinner("Loading demo data…"):
                st.session_state["all_data"] = gen_demo_sprint()
                st.session_state["loaded"] = True
        elif st.session_state.get("pat") and "YOUR_ORG" not in st.session_state.get("org_url",""):
            from concurrent.futures import ThreadPoolExecutor, as_completed

            org = st.session_state["org_url"]
            proj = st.session_state["project"]
            pat  = st.session_state["pat"]
            pi_name  = st.session_state.get("current_pi","26R1")
            pi_field = st.session_state.get("pi_field_name","Custom.PI")

            prog = st.progress(0, "Connecting to Azure DevOps…")
            status_ph = st.empty()  # placeholder for live status text
            all_data = [None] * len(TEAMS)
            completed_count = 0

            # Load all 5 teams IN PARALLEL
            def _load_team_wrapper(idx_team):
                idx, team = idx_team
                return idx, load_team(org, proj, pat, team)

            tasks = [(i, team) for i, team in enumerate(TEAMS)]

            with ThreadPoolExecutor(max_workers=5) as ex:
                futures = {ex.submit(_load_team_wrapper, t): t[1] for t in tasks}

                for future in as_completed(futures):
                    task_label = futures[future]
                    try:
                        result = future.result()
                        idx, td = result
                        all_data[idx] = td
                        completed_count += 1
                        pct = completed_count / len(TEAMS)
                        prog.progress(pct, f"Loaded {td.get('team','')} ✓")
                        status_ph.markdown(
                            f'<div style="font-size:11px;color:#6b7280">'
                            f'Loading in parallel… {completed_count}/{len(TEAMS)} teams done</div>',
                            unsafe_allow_html=True)
                    except Exception as e:
                        st.warning(f"Error loading {task_label}: {str(e)[:80]}")

            prog.empty(); status_ph.empty()
            # Fill any None slots (shouldn't happen but safety net)
            all_data = [d for d in all_data if d is not None]
            st.session_state["all_data"] = all_data
            st.session_state["loaded"]   = True

            # PM action items loaded separately on demand
            st.session_state.setdefault("pm_actions", [])
        else:
            # Landing page
            st.markdown("""
            <div style="display:flex;flex-direction:column;align-items:center;
                 justify-content:center;min-height:70vh;text-align:center;padding:20px">
              <div style="font-size:52px;margin-bottom:16px">🚀</div>
              <div style="font-size:28px;font-weight:800;color:#1a202c;margin-bottom:8px">HRM Command Centre</div>
              <div style="font-size:14px;color:#6b7280;line-height:1.8;max-width:420px">
                PI Execution Centre + Sprint Monitor for 5 Scrum Teams.<br>
                Configure Azure DevOps in Streamlit Secrets or connect via sidebar.
              </div>
            </div>
            """, unsafe_allow_html=True)
            _, cc, _ = st.columns([3,2,3])
            with cc:
                if st.button("🧪 Load Demo Data", use_container_width=True):
                    st.session_state.update({"use_demo":True,"loaded":False}); st.rerun()
            return

    # ── PI DATA LOADING — always load fresh when not loaded ──
    if not st.session_state.get("pi_loaded"):
        if st.session_state.get("use_demo"):
            st.session_state["pi_data"]   = gen_demo_pi()
            st.session_state["pi_loaded"] = True
        elif st.session_state.get("pat") and "YOUR_ORG" not in st.session_state.get("org_url",""):
            pi_name  = st.session_state.get("current_pi", "26R1")
            pi_field = st.session_state.get("pi_field_name", "Custom.PI")
            cache_v  = st.session_state.get("cache_version", 0)
            with st.spinner(f"Loading PI {pi_name} features from Azure DevOps..."):
                pi_data_fresh = load_pi_data(
                    st.session_state["org_url"],
                    st.session_state["pat"],
                    pi_name, pi_field, cache_v
                )
            # Store debug info to show after rerun
            st.session_state["pi_debug"] = (
                f"Raw features from API: {pi_data_fresh.get('_raw_count','?')} | "
                f"After status filter: {len(pi_data_fresh.get('features',[]))} | "
                f"Sample state: {pi_data_fresh.get('_sample_state','?')} | "
                f"PI dates: {pi_data_fresh.get('pi_start')} → {pi_data_fresh.get('pi_end')} | "
                f"WIQL error: {st.session_state.get('_wiql_last_error','none')}"
            )
            st.session_state["pi_data"]   = pi_data_fresh
            st.session_state["pi_loaded"] = True
            st.rerun()

    all_data = st.session_state["all_data"]
    pi_data  = st.session_state.get("pi_data", {})

    # Show debug info if available
    if st.session_state.get("pi_debug"):
        st.warning(f"🔍 {st.session_state['pi_debug']}")

    # ── TABS: PI first, Sprint second ──
    tab_pi, tab_sprint = st.tabs(["🚀  PI Execution Centre", "📊  Sprint Monitor"])

    with tab_pi:
        if pi_data:
            # Handle sprint detail navigation from PI board
            if st.session_state.get("view") == "team_detail" and st.session_state.get("active_tab") == "sprint":
                st.info("Switch to Sprint Monitor tab to see team detail.")
            else:
                render_pi_tab(pi_data, all_data)
        else:
            st.info("PI data loading… please wait.")

    with tab_sprint:
        view = st.session_state.get("view","alert_center")
        if view == "alert_center":
            render_sprint_monitor(all_data)
        elif view == "team_detail":
            sel  = st.session_state.get("selected_team", TEAMS[0])
            td   = next((t for t in all_data if t["team"]==sel), None)
            if td:
                render_team_detail(td, all_data)
            else:
                st.session_state["view"] = "alert_center"; st.rerun()

if __name__ == "__main__":
    main()
