"""
╔══════════════════════════════════════════════════════════════════╗
║         SPRINT ALERT CENTER — PI Execution Dashboard            ║
║         5 Scrum Teams · HRM Project · Azure DevOps              ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import base64
from collections import defaultdict
from io import BytesIO

# ──────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sprint Alert Center",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #f8fafc !important;
    color: #0f172a !important;
}
.stApp { background: #f8fafc; }
.block-container { padding: 1.2rem 1.8rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] * { color: #475569 !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebar"] input {
    color: #0f172a !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 11px !important; font-weight: 600 !important; }

.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    transition: all 0.15s !important;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #475569 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
.stButton > button:hover {
    border-color: #3b82f6 !important;
    color: #3b82f6 !important;
    background: #eff6ff !important;
}

div[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #64748b !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #0f172a !important;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────
TEAMS = ["Echo Engineers", "Code Commanders", "Beta Brigade", "Gamma Guardians", "Hyper Hackers"]
TEAM_AVATARS   = {"Echo Engineers":"⚡","Code Commanders":"🛡️","Beta Brigade":"🔥","Gamma Guardians":"🌀","Hyper Hackers":"💥"}
TEAM_COLORS    = {"Echo Engineers":"#3b82f6","Code Commanders":"#8b5cf6","Beta Brigade":"#f97316","Gamma Guardians":"#10b981","Hyper Hackers":"#ec4899"}
COMPLETED      = ["Done", "Resolved", "Dev Completed"]
INPROGRESS     = ["In Progress", "Scheduled"]
VALID_TYPES    = ["Task", "Bug"]

HEALTH_CFG = {
    "critical": {"color":"#dc2626","bg":"#fef2f2","border":"#fca5a5","label":"CRITICAL","icon":"🔴"},
    "atrisk":   {"color":"#ea580c","bg":"#fff7ed","border":"#fdba74","label":"AT RISK",  "icon":"🟠"},
    "watch":    {"color":"#ca8a04","bg":"#fefce8","border":"#fde047","label":"WATCH",    "icon":"🟡"},
    "healthy":  {"color":"#16a34a","bg":"#f0fdf4","border":"#86efac","label":"HEALTHY",  "icon":"🟢"},
    "no_data":  {"color":"#64748b","bg":"#f8fafc","border":"#cbd5e1","label":"NO DATA",  "icon":"⚫"},
}

BLOCKED_TAGS = {
    "Env-Unstable":    {"label":"Environment Unstable",  "icon":"🌩️","color":"#7c3aed","bg":"#f5f3ff","border":"#c4b5fd","owner":"DevOps Team",    "desc":"Env is unstable — cannot test/deploy"},
    "PR-Approval":     {"label":"PR Awaiting Approval",  "icon":"🔀","color":"#1d4ed8","bg":"#eff6ff","border":"#93c5fd","owner":"Tech Lead / Peer","desc":"Pull request waiting for code review"},
    "Test-Data-Issue": {"label":"Test Data Issue",       "icon":"🗄️","color":"#c2410c","bg":"#fff7ed","border":"#fdba74","owner":"BA / QA Lead",   "desc":"Missing or incorrect test data"},
    "Blocked":         {"label":"Blocked",               "icon":"🚧","color":"#dc2626","bg":"#fef2f2","border":"#fca5a5","owner":"Scrum Master",   "desc":"Blocked — escalation required"},
}

FLAG_COLORS = {
    "spill_high":  {"color":"#dc2626","bg":"#fef2f2","border":"#fca5a5","label":"🔴 HIGH RISK"},
    "spill_watch": {"color":"#ca8a04","bg":"#fefce8","border":"#fde047","label":"🟡 WATCH"},
    "overburn":    {"color":"#ea580c","bg":"#fff7ed","border":"#fdba74","label":"🔥 OVERBURN"},
    "blocked":     {"color":"#7c3aed","bg":"#f5f3ff","border":"#c4b5fd","label":"🚧 BLOCKED"},
    "unestimated": {"color":"#0891b2","bg":"#ecfeff","border":"#67e8f9","label":"📋 NO ESTIMATE"},
    "date_violation":{"color":"#be185d","bg":"#fdf2f8","border":"#f9a8d4","label":"📅 DATE ISSUE"},
}

# ──────────────────────────────────────────────────────────────────
# AZURE DEVOPS CLIENT
# ──────────────────────────────────────────────────────────────────
class DevOpsClient:
    def __init__(self, org, proj, pat):
        self.org  = org.rstrip("/")
        self.proj = proj
        tok       = base64.b64encode(f":{pat}".encode()).decode()
        self.h    = {"Authorization": f"Basic {tok}", "Content-Type": "application/json"}

    def _get(self, url, params=None):
        try:
            r = requests.get(url, headers=self.h, params=params, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return None

    def _post(self, url, body):
        try:
            r = requests.post(url, headers=self.h, json=body, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return None

    def get_sprint(self, team):
        """Get current sprint, fallback to most recent past sprint."""
        base = f"{self.org}/{self.proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations"
        # Try current first
        d = self._get(base, {"$timeframe": "current", "api-version": "7.0"})
        if d and d.get("value"):
            sp = d["value"][0]
            sp["_timeframe"] = "current"
            return sp
        # Fallback to most recent past
        d = self._get(base, {"$timeframe": "past", "api-version": "7.0"})
        if d and d.get("value"):
            # Sort by finish date descending, take most recent
            sprints = d["value"]
            sprints.sort(key=lambda x: x.get("attributes", {}).get("finishDate", ""), reverse=True)
            sp = sprints[0]
            sp["_timeframe"] = "past"
            return sp
        return None

    def get_sprint_wi_ids(self, team, iteration_id):
        """Get all work item IDs in a sprint iteration."""
        url  = f"{self.org}/{self.proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations/{iteration_id}/workitems"
        data = self._get(url, {"api-version": "7.0"})
        if not data:
            return []
        ids = []
        for wi in data.get("workItemRelations", []):
            try:
                target = wi.get("target")
                if target and target.get("id"):
                    ids.append(target["id"])
            except Exception:
                continue
        return list(set(ids))  # deduplicate

    def get_wi_batch(self, ids):
        """Fetch work item details in batches of 200."""
        if not ids:
            return []
        fields = [
            "System.Id", "System.Title", "System.WorkItemType",
            "System.State", "System.AssignedTo", "System.Parent",
            "Microsoft.VSTS.Scheduling.OriginalEstimate",
            "Microsoft.VSTS.Scheduling.CompletedWork",
            "Microsoft.VSTS.Scheduling.RemainingWork",
            "Microsoft.VSTS.Common.Priority",
            "Microsoft.VSTS.Common.Activity",
            "System.Tags", "System.IterationPath",
            "Microsoft.VSTS.Scheduling.StartDate",
            "Microsoft.VSTS.Scheduling.TargetDate",
        ]
        out = []
        for i in range(0, len(ids), 200):
            d = self._post(
                f"{self.org}/_apis/wit/workitemsbatch?api-version=7.0",
                {"ids": ids[i:i+200], "fields": fields}
            )
            if d:
                out.extend(d.get("value", []))
        return out

# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────
def working_hours_left(sprint_end):
    if not sprint_end:
        return 0
    today = date.today()
    if today > sprint_end:
        return 0
    count = 0
    cur   = today
    while cur <= sprint_end:
        if cur.weekday() < 5:
            count += 1
        cur = date.fromordinal(cur.toordinal() + 1)
    return count * 8

def working_days_left(sprint_end):
    if not sprint_end:
        return 0
    today = date.today()
    if today > sprint_end:
        return 0
    count = 0
    cur   = today
    while cur <= sprint_end:
        if cur.weekday() < 5:
            count += 1
        cur = date.fromordinal(cur.toordinal() + 1)
    return count

def parse_date(val):
    if not val:
        return None
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def initials(name):
    parts = str(name).split()
    return "".join(p[0] for p in parts[:2]).upper() if parts else "?"

def detect_blocked(tags_str):
    """Parse semicolon-separated tags and return matched blocked configs."""
    if not tags_str:
        return []
    tags    = [t.strip() for t in str(tags_str).split(";")]
    matched = []
    # Check specific combos first (Blocked + sub-tag)
    has_blocked = "Blocked" in tags
    if has_blocked:
        for sub in ["Env-Unstable", "PR-Approval", "Test-Data-Issue"]:
            if sub in tags:
                matched.append((sub, BLOCKED_TAGS[sub]))
        if not matched:
            matched.append(("Blocked", BLOCKED_TAGS["Blocked"]))
    return matched

def check_date_violation(item_start, item_target, sprint_start, sprint_end):
    """Check if start/target dates are blank or outside sprint boundary."""
    violations = []
    if not item_start:
        violations.append("Start date not set")
    elif sprint_start and item_start < sprint_start:
        violations.append(f"Start date {item_start.strftime('%b %d')} before sprint start")
    elif sprint_end and item_start > sprint_end:
        violations.append(f"Start date {item_start.strftime('%b %d')} after sprint end")
    if not item_target:
        violations.append("Target date not set")
    elif sprint_end and item_target > sprint_end:
        violations.append(f"Target date {item_target.strftime('%b %d')} beyond sprint end")
    return violations

def classify_spill(item, hl):
    """Returns (risk_tier, reasons). Tiers: 'none' | 'watch' | 'high'."""
    state = item.get("state", "")
    est   = item.get("est", 0) or 0
    done  = item.get("done", 0) or 0
    rem   = item.get("rem", 0) or 0
    if state in COMPLETED:
        return "none", []
    is_ip   = state in INPROGRESS
    is_todo = state == "To Do"
    is_hold = state == "On hold"
    total   = done + rem
    prog    = (done / total) if total > 0 else 0
    risk    = "none"
    reasons = []
    # HIGH
    if is_hold:
        risk = "high"; reasons.append("Blocked — On Hold")
    if is_todo and rem > hl and hl > 0:
        risk = "high"; reasons.append(f"Not started · {rem}h needed, only {hl}h left")
    if state == "Scheduled" and rem > hl and hl > 0:
        risk = "high"; reasons.append(f"Scheduled · {rem}h remaining > {hl}h available")
    target_dt  = item.get("target_date")
    sprint_end = item.get("sprint_end")
    if target_dt and sprint_end and target_dt > sprint_end:
        risk = "high"; reasons.append(f"Target date {target_dt.strftime('%b %d')} is past sprint end")
    # WATCH
    if risk != "high":
        if is_todo and 0 < rem <= hl and rem > 4:
            risk = "watch"; reasons.append(f"Not started · {rem}h remaining")
        if is_ip and total > 4 and prog < 0.3:
            risk = "watch"; reasons.append(f"Only {int(prog*100)}% done ({done}h of {total}h)")
        if is_ip and done == 0 and rem > 0:
            risk = "watch"; reasons.append("In Progress — 0 hours logged yet")
        if state == "Scheduled":
            risk = "watch"; reasons.append("Scheduled — not yet activated")
        if is_ip and hl > 0 and rem > (hl * 0.8):
            risk = "watch"; reasons.append(f"{rem}h remaining with limited time left")
    return risk, reasons

def classify_overburn(item):
    """Returns (is_overburn, overrun_hours, effective_total)."""
    state = item.get("state", "")
    est   = item.get("est", 0) or 0
    done  = item.get("done", 0) or 0
    rem   = item.get("rem", 0) or 0
    if est <= 0:
        return False, 0, done
    if state in COMPLETED:
        ov = done - est
        return ov > 0, round(max(ov, 0), 1), round(done, 1)
    elif state in INPROGRESS:
        proj = done + rem
        ov   = proj - est
        return ov > 0, round(max(ov, 0), 1), round(proj, 1)
    return False, 0, done

def score_member(items):
    """Compute risk score for nine-box placement."""
    spill  = sum(3 if i.get("spill_risk") == "high" else 1 if i.get("spill_risk") == "watch" else 0 for i in items)
    over   = sum(2 for i in items if i.get("is_overburn"))
    block  = sum(1 for i in items if i.get("is_blocked"))
    return spill + over + block

def compute_team_health(items):
    """Return health status and counts from item list."""
    tasks      = [i for i in items if i.get("type") in VALID_TYPES] or items
    total      = len(tasks)
    done_c     = sum(1 for i in tasks if i["state"] in COMPLETED)
    high_c     = sum(1 for i in tasks if i.get("spill_risk") == "high")
    watch_c    = sum(1 for i in tasks if i.get("spill_risk") == "watch")
    over_c     = sum(1 for i in tasks if i.get("is_overburn"))
    blocked_c  = sum(1 for i in tasks if i.get("is_blocked"))
    comp_pct   = round(done_c / total * 100) if total else 0
    over_pct   = round(over_c / total * 100) if total else 0
    if high_c >= 3 or over_pct >= 30 or blocked_c >= 3:
        health = "critical"
    elif high_c >= 1 or over_pct >= 15 or blocked_c >= 1:
        health = "atrisk"
    elif watch_c >= 1 or over_c > 0:
        health = "watch"
    else:
        health = "healthy"
    return {
        "health": health, "total": total, "done_count": done_c,
        "high_count": high_c, "watch_count": watch_c,
        "over_count": over_c, "blocked_count": blocked_c,
        "comp_pct": comp_pct,
    }

# ──────────────────────────────────────────────────────────────────
# DATA LOADER
# ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_team(org, proj, pat, team):
    cl = DevOpsClient(org, proj, pat)

    # ── Sprint ──
    sprint = cl.get_sprint(team)
    if not sprint:
        return {
            "team": team, "error": "No sprint found",
            "items": [], "health": "no_data",
            "total": 0, "done_count": 0, "high_count": 0,
            "watch_count": 0, "over_count": 0, "blocked_count": 0, "comp_pct": 0
        }

    attrs       = sprint.get("attributes", {})
    sprint_name = sprint.get("name", "")
    timeframe   = sprint.get("_timeframe", "current")
    sprint_start= parse_date(attrs.get("startDate"))
    sprint_end  = parse_date(attrs.get("finishDate"))
    hl          = working_hours_left(sprint_end)
    dl          = working_days_left(sprint_end)

    # ── Work Item IDs ──
    ids = cl.get_sprint_wi_ids(team, sprint.get("id", ""))
    if not ids:
        h = compute_team_health([])
        return {
            "team": team, "sprint_name": sprint_name, "timeframe": timeframe,
            "sprint_start": sprint_start, "sprint_end": sprint_end,
            "hrs_left": hl, "days_left": dl, "items": [], **h
        }

    # ── Work Items ──
    raw      = cl.get_wi_batch(ids)
    parent_ids = set()
    items    = []

    for wi in raw:
        f  = wi.get("fields", {})
        wtype = f.get("System.WorkItemType", "")
        if wtype not in VALID_TYPES:
            continue
        af       = f.get("System.AssignedTo", {})
        assignee = af.get("displayName", "Unassigned") if isinstance(af, dict) else str(af or "Unassigned")
        pid      = f.get("System.Parent")
        if pid:
            parent_ids.add(pid)
        tags_str    = f.get("System.Tags", "") or ""
        item_start  = parse_date(f.get("Microsoft.VSTS.Scheduling.StartDate"))
        item_target = parse_date(f.get("Microsoft.VSTS.Scheduling.TargetDate"))

        item = {
            "id":           wi.get("id"),
            "title":        f.get("System.Title", ""),
            "type":         wtype,
            "state":        f.get("System.State", ""),
            "assignee":     assignee,
            "est":          f.get("Microsoft.VSTS.Scheduling.OriginalEstimate") or 0,
            "done":         f.get("Microsoft.VSTS.Scheduling.CompletedWork") or 0,
            "rem":          f.get("Microsoft.VSTS.Scheduling.RemainingWork") or 0,
            "priority":     f.get("Microsoft.VSTS.Common.Priority", 3),
            "activity":     f.get("Microsoft.VSTS.Common.Activity", ""),
            "tags":         tags_str,
            "item_start":   item_start,
            "item_target":  item_target,
            "parent_id":    pid,
            "sprint_name":  sprint_name,
            "sprint_start": sprint_start,
            "sprint_end":   sprint_end,
            "team":         team,
            "devops_url":   f"{org}/{proj}/_workitems/edit/{wi.get('id')}",
            "backlog_title":"", "backlog_url": "#",
            "feature_title":"", "feature_url": "#",
        }

        # Risk classifications
        sr, rr      = classify_spill(item, hl)
        iso, ov, pj = classify_overburn(item)
        bt          = detect_blocked(tags_str)
        dv          = check_date_violation(item_start, item_target, sprint_start, sprint_end)
        unest       = (item["est"] or 0) == 0

        item["spill_risk"]      = sr
        item["spill_reasons"]   = rr
        item["is_overburn"]     = iso
        item["overrun"]         = ov
        item["projected"]       = pj
        item["blocked_tags"]    = bt
        item["is_blocked"]      = len(bt) > 0
        item["date_violations"] = dv
        item["has_date_issue"]  = len(dv) > 0
        item["is_unestimated"]  = unest and item["state"] not in COMPLETED
        items.append(item)

    # ── Parent Chain (Backlog → Feature) ──
    if parent_ids:
        parents = cl.get_wi_batch(list(parent_ids))
        gp_ids  = set()
        pmap    = {}
        for p in parents:
            f   = p.get("fields", {})
            pid = p.get("id")
            pmap[pid] = {
                "title": f.get("System.Title", ""),
                "parent_id": f.get("System.Parent"),
                "url": f"{org}/{proj}/_workitems/edit/{pid}"
            }
            if f.get("System.Parent"):
                gp_ids.add(f["System.Parent"])

        gpmap = {}
        if gp_ids:
            gps = cl.get_wi_batch(list(gp_ids))
            for gp in gps:
                f    = gp.get("fields", {})
                gpid = gp.get("id")
                gpmap[gpid] = {
                    "title": f.get("System.Title", ""),
                    "url": f"{org}/{proj}/_workitems/edit/{gpid}"
                }

        for item in items:
            pid = item.get("parent_id")
            if pid and pid in pmap:
                item["backlog_title"] = pmap[pid]["title"]
                item["backlog_url"]   = pmap[pid]["url"]
                gpid = pmap[pid].get("parent_id")
                if gpid and gpid in gpmap:
                    item["feature_title"] = gpmap[gpid]["title"]
                    item["feature_url"]   = gpmap[gpid]["url"]

    h = compute_team_health(items)
    return {
        "team": team, "sprint_name": sprint_name, "timeframe": timeframe,
        "sprint_start": sprint_start, "sprint_end": sprint_end,
        "hrs_left": hl, "days_left": dl, "items": items, **h
    }

# ──────────────────────────────────────────────────────────────────
# DEMO DATA
# ──────────────────────────────────────────────────────────────────
def gen_demo():
    from random import seed, randint, choice, random, uniform
    seed(42)
    today = date.today()
    cfgs = {
        "Echo Engineers":  {"h":3,"w":2,"o":4,"b":2,"dp":0.45,"start":date(2026,5,4),"end":date(2026,5,15)},
        "Code Commanders": {"h":1,"w":3,"o":2,"b":1,"dp":0.62,"start":date(2026,5,4),"end":date(2026,5,15)},
        "Beta Brigade":    {"h":2,"w":2,"o":3,"b":2,"dp":0.50,"start":date(2026,4,27),"end":date(2026,5,8)},
        "Gamma Guardians": {"h":0,"w":2,"o":1,"b":0,"dp":0.75,"start":date(2026,5,4),"end":date(2026,5,15)},
        "Hyper Hackers":   {"h":0,"w":0,"o":0,"b":0,"dp":0.88,"start":date(2026,4,27),"end":date(2026,5,8)},
    }
    feats = ["Employee Info Module v2","Payroll Engine","Leave Management","Performance Portal","Recruitment Flow"]
    bls   = ["API Layer Implementation","Test Coverage","UI Revamp","Data Migration","Integration Testing","Documentation"]
    mems  = {
        "Echo Engineers":  ["Amila F.","Chamod B.","Hansani G.","Sharini N.","Udara W.","Luqman R."],
        "Code Commanders": ["Kasun B.","Praveena G.","Nadith L.","Michelle P.","Iran U.","Maksudul R."],
        "Beta Brigade":    ["Sammani E.","Mihirani G.","Liyathambara G.","Alex K.","Priya M.","Suresh T."],
        "Gamma Guardians": ["Nadia R.","Chen W.","Omar B.","Tara L.","Dev S.","Kim H."],
        "Hyper Hackers":   ["Raj P.","Fatima A.","Tom B.","Sara L.","Mei X.","Janaka K."],
    }
    block_tags = ["Blocked; Env-Unstable","Blocked; PR-Approval","Blocked; Test-Data-Issue"]
    all_data = []
    iid = 130000

    for team, cfg in cfgs.items():
        items   = []
        n       = randint(18, 28)
        tm      = mems[team]
        ss      = cfg["start"]
        se      = cfg["end"]
        hl      = working_hours_left(se)
        dl      = working_days_left(se)
        tf      = "current" if today <= se else "past"

        for j in range(n):
            iid  += 1
            feat  = feats[j % 5]
            bl    = bls[j % 6]
            mem   = tm[j % len(tm)]
            is_h  = j < cfg["h"]
            is_w  = cfg["h"] <= j < cfg["h"] + cfg["w"]
            is_o  = j < cfg["o"]
            is_b  = j < cfg["b"]
            is_d  = random() < cfg["dp"]

            if is_d:    state = choice(["Done","Done","Resolved","Dev Completed"])
            elif is_h:  state = choice(["To Do","On hold","Scheduled"])
            elif is_w:  state = choice(["In Progress","To Do"])
            else:       state = choice(["To Do","In Progress","Done"])

            est = round(randint(2, 16) * 0.5, 1) if j % 8 != 0 else 0  # some unestimated

            if state in COMPLETED:
                done_h = round(est * (1.3 if is_o else uniform(0.7, 1.0)), 1) if est > 0 else round(uniform(1, 8), 1)
                rem_h  = 0
            elif state == "In Progress":
                done_h = round(est * uniform(0.1, 0.5), 1) if est > 0 else 0
                rem_h  = round((est * 1.4 - done_h) if is_o else max(est - done_h + uniform(0, 2), 0), 1) if est > 0 else round(uniform(2, 8), 1)
            else:
                done_h = 0
                rem_h  = est if not is_h else round(est + randint(8, 20), 1)

            # Tags
            if is_b and state not in COMPLETED:
                tags_str = choice(block_tags)
            else:
                tags_str = "26R1"

            # Date violations for some items
            if j % 10 == 0:
                item_start  = None  # missing start
                item_target = None  # missing target
            elif j % 13 == 0:
                item_start  = date(2026, 4, 1)  # before sprint
                item_target = date(2026, 5, 30)  # after sprint
            else:
                item_start  = ss
                item_target = se

            item = {
                "id": iid, "title": f"[{'DEV' if j%3==0 else 'QA' if j%3==1 else 'BA'}] {bl} — {feat[:35]}",
                "type": choice(["Task","Task","Task","Bug"]),
                "state": state, "assignee": mem,
                "est": est, "done": round(done_h, 1), "rem": round(max(rem_h, 0), 1),
                "priority": randint(1, 3), "activity": choice(["Development","Testing","Documentation"]),
                "tags": tags_str, "item_start": item_start, "item_target": item_target,
                "parent_id": 120000 + j, "sprint_name": f"26R1_SP{'05' if tf=='past' else '06'}",
                "sprint_start": ss, "sprint_end": se, "team": team, "timeframe": tf,
                "devops_url": f"https://dev.azure.com/demo/HRM/_workitems/edit/{iid}",
                "backlog_title": bl, "backlog_url": f"https://dev.azure.com/demo/HRM/_workitems/edit/{120000+j}",
                "feature_title": feat, "feature_url": f"https://dev.azure.com/demo/HRM/_workitems/edit/{110000+(j%5)}",
            }

            sr, rr      = classify_spill(item, hl)
            iso, ov, pj = classify_overburn(item)
            bt          = detect_blocked(tags_str)
            dv          = check_date_violation(item_start, item_target, ss, se)
            unest       = (est or 0) == 0

            item["spill_risk"]      = sr
            item["spill_reasons"]   = rr
            item["is_overburn"]     = iso
            item["overrun"]         = ov
            item["projected"]       = pj
            item["blocked_tags"]    = bt
            item["is_blocked"]      = len(bt) > 0
            item["date_violations"] = dv
            item["has_date_issue"]  = len(dv) > 0
            item["is_unestimated"]  = unest and state not in COMPLETED
            items.append(item)

        h = compute_team_health(items)
        all_data.append({
            "team": team, "sprint_name": f"26R1_SP{'05' if tf=='past' else '06'}",
            "timeframe": tf, "sprint_start": ss, "sprint_end": se,
            "hrs_left": hl, "days_left": dl, "items": items, **h
        })

    return all_data

# ──────────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ──────────────────────────────────────────────────────────────────
def build_excel(all_data):
    rows = []
    for tdata in all_data:
        team = tdata.get("team", "")
        for i in tdata.get("items", []):
            rows.append({
                "Work Item ID":    i.get("id"),
                "Title":           i.get("title", ""),
                "Type":            i.get("type", ""),
                "State":           i.get("state", ""),
                "Assigned To":     i.get("assignee", ""),
                "Team":            team,
                "Sprint":          i.get("sprint_name", ""),
                "Sprint Start":    str(i.get("sprint_start", "")),
                "Sprint End":      str(i.get("sprint_end", "")),
                "Original Est (h)":i.get("est", 0),
                "Completed (h)":   i.get("done", 0),
                "Remaining (h)":   i.get("rem", 0),
                "Projected (h)":   i.get("projected", 0),
                "Spill Risk":      i.get("spill_risk", "none").upper(),
                "Spill Reasons":   " | ".join(i.get("spill_reasons", [])),
                "Is Overburn":     "YES" if i.get("is_overburn") else "NO",
                "Overrun (h)":     i.get("overrun", 0),
                "Is Blocked":      "YES" if i.get("is_blocked") else "NO",
                "Blocked Tags":    i.get("tags", ""),
                "Is Unestimated":  "YES" if i.get("is_unestimated") else "NO",
                "Date Violation":  "YES" if i.get("has_date_issue") else "NO",
                "Date Issues":     " | ".join(i.get("date_violations", [])),
                "Item Start Date": str(i.get("item_start", "")),
                "Item Target Date":str(i.get("item_target", "")),
                "Feature":         i.get("feature_title", ""),
                "Backlog Item":    i.get("backlog_title", ""),
                "DevOps URL":      i.get("devops_url", ""),
            })
    df = pd.DataFrame(rows)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sprint Data")
        ws = writer.sheets["Sprint Data"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)
    buf.seek(0)
    return buf

# ──────────────────────────────────────────────────────────────────
# UI COMPONENTS
# ──────────────────────────────────────────────────────────────────
def flag_pill(key):
    c = FLAG_COLORS.get(key, {})
    return (f'<span style="background:{c.get("bg","#f1f5f9")};color:{c.get("color","#475569")};'
            f'border:1px solid {c.get("border","#e2e8f0")};border-radius:4px;padding:2px 8px;'
            f'font-size:10px;font-weight:700;white-space:nowrap">{c.get("label","?")}</span>')

def health_badge(status, size=11):
    c = HEALTH_CFG.get(status, HEALTH_CFG["no_data"])
    return (f'<span style="background:{c["bg"]};color:{c["color"]};'
            f'border:1px solid {c["border"]};border-radius:4px;padding:2px 10px;'
            f'font-size:{size}px;font-weight:700">{c["icon"]} {c["label"]}</span>')

def item_card(item, all_data, mode="spill"):
    """Render a single item card for spillover, overburn, or blocked view."""
    team      = item.get("team", "")
    tcolor    = TEAM_COLORS.get(team, "#64748b")
    sr        = item.get("spill_risk", "none")
    iso       = item.get("is_overburn", False)
    is_b      = item.get("is_blocked", False)
    unest     = item.get("is_unestimated", False)
    date_iss  = item.get("has_date_issue", False)

    # Border color based on mode
    if mode == "spill":
        bc = "#dc2626" if sr == "high" else "#ca8a04"
    elif mode == "overburn":
        bc = "#dc2626" if (item.get("projected",0) / item.get("est",1) * 100 if item.get("est",0)>0 else 0) >= 150 else "#ea580c"
    elif mode == "blocked":
        first_tag = item.get("blocked_tags", [("Blocked", BLOCKED_TAGS["Blocked"])])[0]
        bc = BLOCKED_TAGS.get(first_tag[0], BLOCKED_TAGS["Blocked"])["color"]
    else:
        bc = "#64748b"

    # Build flag pills
    pills = []
    if sr == "high":   pills.append(flag_pill("spill_high"))
    elif sr == "watch":pills.append(flag_pill("spill_watch"))
    if iso:            pills.append(flag_pill("overburn"))
    if is_b:           pills.append(flag_pill("blocked"))
    if unest:          pills.append(flag_pill("unestimated"))
    if date_iss:       pills.append(flag_pill("date_violation"))
    pills_html = " ".join(pills)

    # Links
    bl_html = (f'<a href="{item.get("backlog_url","#")}" target="_blank" style="color:#64748b;font-size:10px;text-decoration:none;hover:underline">'
               f'{item.get("backlog_title","")[:40]}</a>' if item.get("backlog_title") else "")
    ft_html = (f'<a href="{item.get("feature_url","#")}" target="_blank" style="color:#2563eb;font-size:10px;font-weight:600;text-decoration:none">'
               f'📌 {item.get("feature_title","")[:45]}</a>' if item.get("feature_title") else "")
    breadcrumb = " › ".join(filter(None, [bl_html, ft_html]))

    # Reasons / details
    if mode == "spill":
        detail = " · ".join(item.get("spill_reasons", []))
    elif mode == "overburn":
        est = item.get("est", 0); proj = item.get("projected", 0); ov = item.get("overrun", 0)
        is_ip = item.get("state") in INPROGRESS
        pct = int(proj / est * 100) if est > 0 else 0
        detail = f"Est: {est}h → {'Projected' if is_ip else 'Actual'}: {proj:.1f}h · Overrun: +{ov:.1f}h ({pct}%)"
    elif mode == "blocked":
        tags_info = " | ".join(f'{cfg["icon"]} {cfg["label"]} → {cfg["owner"]}' for _, cfg in item.get("blocked_tags", []))
        detail = tags_info
    else:
        detail = ""

    # Sprint context (show if past sprint)
    sprint_badge = ""
    if item.get("timeframe") == "past":
        sprint_badge = f'<span style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;border-radius:3px;padding:1px 6px;font-size:9px;font-weight:700;margin-left:6px">📅 LAST SPRINT</span>'

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:4px solid {bc};'
        f'border-radius:8px;padding:14px 18px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.05)">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px">'
        f'<div style="flex:1;min-width:0">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;flex-wrap:wrap">'
        f'<a href="{item.get("devops_url","#")}" target="_blank" '
        f'style="color:#2563eb;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;text-decoration:none">#{item["id"]}</a>'
        f'{sprint_badge}'
        f'<span style="color:#0f172a;font-size:13px;font-weight:600">{item["title"][:70]}{"…" if len(item["title"])>70 else ""}</span>'
        f'</div>'
        f'<div style="font-size:10px;color:#64748b;margin-bottom:6px">'
        f'<span style="color:{tcolor};font-weight:600">{team}</span>'
        f'{(" › " + breadcrumb) if breadcrumb else ""}'
        f'</div>'
        f'<div style="font-size:11px;color:#475569;font-style:italic;margin-bottom:6px">⚡ {detail}</div>'
        f'<div style="display:flex;gap:4px;flex-wrap:wrap">{pills_html}</div>'
        f'</div>'
        f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;min-width:100px">'
        f'<span style="font-size:11px;color:#475569;font-weight:600">{item.get("assignee","—")}</span>'
        f'<span style="background:#f1f5f9;color:#475569;border-radius:4px;padding:1px 8px;font-size:10px">{item.get("state","—")}</span>'
        f'<span style="font-size:11px;color:#ca8a04;font-weight:600">{item.get("rem",0)}h rem</span>'
        + ('<span style="font-size:10px;color:#64748b">⚡ Projected</span>' if item.get("state") in INPROGRESS and mode=="overburn" else "")
        + f'</div></div></div>',
        unsafe_allow_html=True
    )

# ──────────────────────────────────────────────────────────────────
# NINE-BOX GRID
# ──────────────────────────────────────────────────────────────────
def render_nine_box(all_data):
    """Render an interactive nine-box grid across all team members."""
    members = defaultdict(lambda: {"items": [], "team": ""})
    for tdata in all_data:
        team  = tdata.get("team", "")
        for item in tdata.get("items", []):
            a = item.get("assignee", "Unassigned")
            members[a]["items"].append(item)
            members[a]["team"] = team

    dots = []
    for name, data in members.items():
        items    = data["items"]
        team     = data["team"]
        total    = len(items)
        if total == 0:
            continue
        done_c   = sum(1 for i in items if i["state"] in COMPLETED)
        comp_pct = round(done_c / total * 100)
        risk_sc  = score_member(items)
        est_hrs  = sum(i.get("est", 0) or 0 for i in items)
        spill_c  = sum(1 for i in items if i.get("spill_risk") in ["high","watch"])
        over_c   = sum(1 for i in items if i.get("is_overburn"))
        block_c  = sum(1 for i in items if i.get("is_blocked"))

        # Dot color: dominant issue
        if sum(1 for i in items if i.get("spill_risk") == "high") > 0:
            dot_color = "#dc2626"
        elif over_c > 0 and block_c > 0:
            dot_color = "#7c3aed"
        elif over_c > 0:
            dot_color = "#ea580c"
        elif block_c > 0:
            dot_color = "#7c3aed"
        elif spill_c > 0:
            dot_color = "#ca8a04"
        else:
            dot_color = "#16a34a"

        # Normalize risk score to 0-100 scale (max possible ~20)
        risk_norm = min(risk_sc * 5, 100)
        dot_size  = max(10, min(est_hrs * 1.5, 40))

        # Show name on dot if in critical quadrant (high risk, low delivery)
        in_critical = risk_norm > 60 and comp_pct < 40
        label = f"{initials(name)}" if not in_critical else name.split()[0]

        dots.append({
            "name": name, "team": team,
            "x": comp_pct, "y": risk_norm,
            "size": dot_size, "color": dot_color,
            "label": label, "in_critical": in_critical,
            "comp_pct": comp_pct, "risk_score": risk_sc,
            "spill": spill_c, "over": over_c, "block": block_c,
            "total": total, "est_hrs": est_hrs,
            "has_blocked": block_c > 0,
        })

    if not dots:
        st.info("No member data available.")
        return

    # Build plotly figure
    fig = go.Figure()

    # Quadrant backgrounds
    quads = [
        (0, 0,  40, 33,  "#fef2f2", "CRITICAL"),
        (40, 0, 75, 33,  "#fff7ed", "AT RISK"),
        (75, 0, 100,33,  "#fefce8", "STRUGGLING"),
        (0, 33, 40, 66,  "#fff7ed", "AT RISK"),
        (40,33, 75, 66,  "#fefce8", "WATCH"),
        (75,33, 100,66,  "#f0fdf4", "STRETCHED"),
        (0, 66, 40, 100, "#fefce8", "SLOW"),
        (40,66, 75, 100, "#f0fdf4", "ON TRACK"),
        (75,66, 100,100, "#f0fdf4", "⭐ STAR"),
    ]

    for x0,y0,x1,y1,color,label in quads:
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                      fillcolor=color, line=dict(color="#e2e8f0", width=1))
        fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=label,
                           font=dict(size=9, color="#94a3b8", family="Inter"),
                           showarrow=False, opacity=0.7)

    # Grid lines
    for v in [40, 75]:
        fig.add_shape(type="line", x0=v, y0=0, x1=v, y1=100,
                      line=dict(color="#e2e8f0", width=1, dash="dot"))
    for h in [33, 66]:
        fig.add_shape(type="line", x0=0, y0=h, x1=100, y1=h,
                      line=dict(color="#e2e8f0", width=1, dash="dot"))

    # Plot each member
    for d in dots:
        team_color = TEAM_COLORS.get(d["team"], "#64748b")
        # Purple ring for blocked
        if d["has_blocked"]:
            fig.add_trace(go.Scatter(
                x=[d["x"]], y=[d["y"]],
                mode="markers",
                marker=dict(size=d["size"]+10, color="rgba(124,58,237,0.2)",
                            line=dict(color="#7c3aed", width=2)),
                showlegend=False, hoverinfo="skip"
            ))

        fig.add_trace(go.Scatter(
            x=[d["x"]], y=[d["y"]],
            mode="markers+text",
            marker=dict(
                size=d["size"],
                color=d["color"],
                line=dict(color=team_color, width=2),
                opacity=0.85,
            ),
            text=d["label"],
            textposition="middle center",
            textfont=dict(size=8, color="#ffffff", family="Inter"),
            hovertemplate=(
                f"<b>{d['name']}</b><br>"
                f"Team: {d['team']}<br>"
                f"Completion: {d['comp_pct']}%<br>"
                f"Risk Score: {d['risk_score']}<br>"
                f"Spill Risk: {d['spill']} items<br>"
                f"Overburn: {d['over']} items<br>"
                f"Blocked: {d['block']} items<br>"
                f"Total Items: {d['total']}<br>"
                f"Est Hours: {d['est_hrs']:.0f}h"
                "<extra></extra>"
            ),
            showlegend=False,
            name=d["name"],
        ))

    fig.update_layout(
        height=420,
        margin=dict(l=50, r=20, t=40, b=50),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        xaxis=dict(
            title="Sprint Completion %",
            range=[0, 100], dtick=25,
            showgrid=False, zeroline=False,
            tickfont=dict(size=10, family="Inter"),
            titlefont=dict(size=11, family="Inter", color="#64748b"),
        ),
        yaxis=dict(
            title="Risk Score (Spill + Overburn + Blocked)",
            range=[0, 100], dtick=33,
            showgrid=False, zeroline=False,
            tickfont=dict(size=10, family="Inter"),
            titlefont=dict(size=11, family="Inter", color="#64748b"),
        ),
        title=dict(
            text="Member Performance Nine-Box · All Teams",
            font=dict(size=14, family="Inter", color="#0f172a"),
            x=0.01, xanchor="left",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legend
    legend_items = [
        ("🔴 High Spill Risk", "#dc2626"),
        ("🟠 Overburn",        "#ea580c"),
        ("🟡 Watch / At Risk", "#ca8a04"),
        ("🟢 Clean",           "#16a34a"),
        ("🟣 Blocked (ring)",  "#7c3aed"),
    ]
    cols = st.columns(len(legend_items))
    for col, (label, color) in zip(cols, legend_items):
        col.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#475569">'
            f'<div style="width:12px;height:12px;border-radius:50%;background:{color}"></div>'
            f'{label}</div>',
            unsafe_allow_html=True
        )

# ──────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="padding:4px 0 20px 0">'
            '<div style="font-size:20px;font-weight:900;color:#0f172a;letter-spacing:-0.5px">🚨 Sprint Alerts</div>'
            '<div style="font-size:10px;color:#94a3b8;margin-top:2px;font-weight:600">Azure DevOps · HRM Project</div>'
            '</div>',
            unsafe_allow_html=True
        )
        org  = st.text_input("Org URL",          value=st.session_state.get("org_url", "https://dev.azure.com/YOUR_ORG"))
        proj = st.text_input("Project Name",     value=st.session_state.get("project", "HRM"))
        pat  = st.text_input("Personal Access Token", value=st.session_state.get("pat", ""), type="password")

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Load Live", use_container_width=True):
                if org and proj and pat:
                    st.session_state.update({"org_url": org, "project": proj, "pat": pat,
                                             "use_demo": False, "loaded": False})
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Fill all fields")
        with c2:
            if st.button("🧪 Demo Data", use_container_width=True):
                st.session_state.update({"use_demo": True, "loaded": False})
                st.rerun()

        if st.session_state.get("loaded"):
            if st.button("🔃 Refresh Now", use_container_width=True):
                st.cache_data.clear()
                st.session_state["loaded"] = False
                st.rerun()

        st.markdown("---")
        st.markdown(
            '<div style="font-size:10px;color:#94a3b8;line-height:1.9">'
            '<b style="color:#64748b">PAT Permissions needed:</b><br>'
            '· Work Items → Read<br>'
            '· Project & Team → Read<br><br>'
            '<b style="color:#64748b">Sprint lookup:</b><br>'
            '· Current sprint first<br>'
            '· Falls back to last sprint<br><br>'
            '<b style="color:#64748b">Data refreshes every 5 min</b>'
            '</div>',
            unsafe_allow_html=True
        )

# ──────────────────────────────────────────────────────────────────
# VIEW 1: ALERT CENTER
# ──────────────────────────────────────────────────────────────────
def render_alert_center(all_data):
    all_items   = [i for t in all_data for i in t.get("items", [])]
    spill_high  = [i for i in all_items if i.get("spill_risk") == "high"]
    spill_watch = [i for i in all_items if i.get("spill_risk") == "watch"]
    overs       = [i for i in all_items if i.get("is_overburn")]
    blocked_all = [i for i in all_items if i.get("is_blocked")]
    both        = [i for i in all_items if i.get("spill_risk") in ["high","watch"] and i.get("is_overburn")]
    total_items = sum(t.get("total", 0) for t in all_data)
    done_items  = sum(t.get("done_count", 0) for t in all_data)
    comp_pct    = round(done_items / total_items * 100) if total_items else 0
    total_ov    = sum(i.get("overrun", 0) for i in overs)
    updated_at  = datetime.now().strftime("%d %b %Y %H:%M")

    # Per-team sprint date analysis
    active = [t for t in all_data if t.get("sprint_end")]
    ends   = [t["sprint_end"] for t in active]
    names  = list(dict.fromkeys(t.get("sprint_name", "") for t in active))
    earliest = min(ends) if ends else None
    latest   = max(ends) if ends else None
    all_same = (earliest == latest) if ends else True
    min_dl   = min((t.get("days_left", 0) for t in active), default=0)
    max_dl   = max((t.get("days_left", 0) for t in active), default=0)

    if all_same and earliest:
        date_str = f"Sprint ends <b style='color:#0f172a'>{earliest.strftime('%b %d, %Y')}</b>"
        days_str = f"<b style='color:{'#dc2626' if min_dl<=2 else '#ea580c' if min_dl<=4 else '#475569'}'>{min_dl} working days left</b>"
    else:
        date_str = f"Sprints end <b style='color:#0f172a'>{earliest.strftime('%b %d') if earliest else '—'} – {latest.strftime('%b %d, %Y') if latest else '—'}</b>"
        days_str = f"<b style='color:#ea580c'>{min_dl}–{max_dl} days left (varies by team)</b>"

    sprint_label = " · ".join(names[:3]) if names else "—"

    # Overall health
    overall = "healthy"
    for t in all_data:
        h = t.get("health", "no_data")
        if h == "critical": overall = "critical"; break
        if h == "atrisk"  and overall != "critical": overall = "atrisk"
        if h == "watch"   and overall not in ["critical","atrisk"]: overall = "watch"
    ocfg = HEALTH_CFG[overall]

    # ── BANNER ──
    past_teams = [t["team"] for t in all_data if t.get("timeframe") == "past"]
    past_note  = f' &nbsp;·&nbsp; <span style="color:#92400e;font-size:11px">📅 {", ".join(past_teams)} showing last sprint</span>' if past_teams else ""

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:5px solid {ocfg["color"]};'
        f'border-radius:10px;padding:20px 28px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div>'
        f'<div style="font-size:10px;color:#94a3b8;letter-spacing:2px;font-weight:700;margin-bottom:4px">🚨 SPRINT ALERT CENTER &nbsp;·&nbsp; {sprint_label}</div>'
        f'<div style="font-size:26px;font-weight:900;color:#0f172a;letter-spacing:-0.5px">Sprint Execution Monitor</div>'
        f'<div style="font-size:12px;color:#64748b;margin-top:4px">'
        f'5 Teams &nbsp;·&nbsp; HRM Project &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp; {days_str}{past_note}'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:9px;color:#94a3b8;font-weight:600;margin-bottom:6px">OVERALL PI STATUS</div>'
        f'<div style="background:{ocfg["bg"]};border:2px solid {ocfg["border"]};border-radius:8px;padding:8px 20px">'
        f'<span style="font-size:18px;font-weight:900;color:{ocfg["color"]}">{ocfg["icon"]} {ocfg["label"]}</span></div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:6px">{comp_pct}% complete &nbsp;·&nbsp; {done_items}/{total_items} items</div>'
        f'<div style="font-size:10px;color:#cbd5e1;margin-top:2px">Last updated: {updated_at}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    # ── 3 ALERT BOXES ──
    sc    = "#dc2626" if spill_high else "#ca8a04" if spill_watch else "#16a34a"
    oc    = "#dc2626" if len(overs) >= 5 else "#ea580c" if overs else "#16a34a"
    bkc   = "#7c3aed" if blocked_all else "#16a34a"
    env_c = sum(1 for i in blocked_all if any(t == "Env-Unstable"    for t, _ in i.get("blocked_tags", [])))
    pr_c  = sum(1 for i in blocked_all if any(t == "PR-Approval"     for t, _ in i.get("blocked_tags", [])))
    td_c  = sum(1 for i in blocked_all if any(t == "Test-Data-Issue" for t, _ in i.get("blocked_tags", [])))

    a1, a2, a3 = st.columns(3)
    for col, color, icon, label, count, detail_html, footer in [
        (a1, sc, "⚠️", "POTENTIAL SPILLOVER",
         len(spill_high)+len(spill_watch),
         f'<div style="text-align:right"><div style="margin-bottom:6px"><span style="font-size:24px;font-weight:800;color:#dc2626">{len(spill_high)}</span> <span style="font-size:11px;color:#dc2626;font-weight:600">HIGH</span></div>'
         f'<div><span style="font-size:24px;font-weight:800;color:#ca8a04">{len(spill_watch)}</span> <span style="font-size:11px;color:#ca8a04;font-weight:600">WATCH</span></div></div>',
         "🔴 Immediate action required" if spill_high else "🟡 Monitor closely" if spill_watch else "✅ Sprint on track"),
        (a2, oc, "🔥", "OVERBURN ALERT",
         len(overs),
         f'<div style="text-align:right"><div style="font-size:10px;color:#94a3b8;margin-bottom:4px">TOTAL OVERRUN</div>'
         f'<div style="font-size:28px;font-weight:800;color:{oc}">+{total_ov:.0f}h</div>'
         f'<div style="font-size:10px;color:#94a3b8">above estimates</div></div>',
         "🔴 Re-plan needed" if total_ov >= 20 else "🟠 Overrun detected" if overs else "✅ All within estimate"),
        (a3, bkc, "🚧", "EXTERNALLY BLOCKED",
         len(blocked_all),
         f'<div style="text-align:right;font-size:11px">'
         f'<div style="margin-bottom:4px"><span style="color:#7c3aed;font-weight:700">🌩️ {env_c}</span> <span style="color:#64748b">Env Issues</span></div>'
         f'<div style="margin-bottom:4px"><span style="color:#1d4ed8;font-weight:700">🔀 {pr_c}</span> <span style="color:#64748b">PR Pending</span></div>'
         f'<div><span style="color:#c2410c;font-weight:700">🗄️ {td_c}</span> <span style="color:#64748b">Test Data</span></div></div>',
         "🚨 Escalate to resolve" if blocked_all else "✅ No external blockers"),
    ]:
        col.markdown(
            f'<div style="background:#ffffff;border:2px solid {color}20;border-top:4px solid {color};'
            f'border-radius:10px;padding:20px 24px;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,0.05)">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
            f'<div><div style="font-size:10px;color:#94a3b8;letter-spacing:1px;font-weight:700;margin-bottom:6px">{icon} {label}</div>'
            f'<div style="font-size:52px;font-weight:900;color:{color};line-height:1">{count}</div>'
            f'</div>{detail_html}</div>'
            f'<div style="margin-top:12px;padding-top:10px;border-top:1px solid #f1f5f9;font-size:11px;color:#64748b">{footer}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── TEAM CARDS ──
    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:#94a3b8;letter-spacing:1.5px;'
        'text-transform:uppercase;margin:8px 0 12px 0">Team Sprint Status</div>',
        unsafe_allow_html=True
    )
    order    = {"critical": 0, "atrisk": 1, "watch": 2, "healthy": 3, "no_data": 4}
    sorted_d = sorted(all_data, key=lambda x: order.get(x.get("health", "no_data"), 4))
    tcols    = st.columns(5)

    for col, td in zip(tcols, sorted_d):
        team  = td.get("team", "")
        h     = td.get("health", "no_data")
        cfg   = HEALTH_CFG[h]
        av    = TEAM_AVATARS.get(team, "🔷")
        hc    = td.get("high_count", 0)
        wc    = td.get("watch_count", 0)
        oc2   = td.get("over_count", 0)
        bk    = td.get("blocked_count", 0)
        cp    = td.get("comp_pct", 0)
        dl    = td.get("days_left", 0)
        se    = td.get("sprint_end")
        sn    = td.get("sprint_name", "—")
        tf    = td.get("timeframe", "current")
        end_l = se.strftime("%b %d") if se else "—"
        dl_c  = "#dc2626" if dl <= 2 else "#ea580c" if dl <= 4 else "#64748b"
        past_b= f'<div style="background:#fef3c7;color:#92400e;border-radius:3px;padding:1px 6px;font-size:8px;font-weight:700;margin-bottom:4px;display:inline-block">📅 LAST SPRINT</div>' if tf == "past" else ""

        with col:
            st.markdown(
                f'<div style="background:#ffffff;border:1.5px solid {cfg["border"]};border-top:4px solid {cfg["color"]};'
                f'border-radius:10px;padding:14px;box-shadow:0 2px 6px rgba(0,0,0,0.05)">'
                f'{past_b}'
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
                f'<span style="font-size:20px">{av}</span>'
                f'<div><div style="font-size:12px;font-weight:700;color:#0f172a;line-height:1.2">{team}</div>'
                f'<div style="font-size:9px;color:{cfg["color"]};font-weight:700;margin-top:1px">{cfg["icon"]} {cfg["label"]}</div></div></div>'
                f'<div style="font-size:9px;color:#94a3b8;margin-bottom:6px">'
                f'{sn} &nbsp;·&nbsp; ends {end_l} &nbsp;·&nbsp; <span style="color:{dl_c};font-weight:700">{dl}d left</span></div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:3px;margin-bottom:10px;text-align:center">'
                f'<div style="background:#fef2f2;border-radius:4px;padding:5px 1px"><div style="font-size:14px;font-weight:800;color:#dc2626">{hc}</div><div style="font-size:7px;color:#94a3b8;font-weight:600">SPILL</div></div>'
                f'<div style="background:#fefce8;border-radius:4px;padding:5px 1px"><div style="font-size:14px;font-weight:800;color:#ca8a04">{wc}</div><div style="font-size:7px;color:#94a3b8;font-weight:600">WATCH</div></div>'
                f'<div style="background:#fff7ed;border-radius:4px;padding:5px 1px"><div style="font-size:14px;font-weight:800;color:#ea580c">{oc2}</div><div style="font-size:7px;color:#94a3b8;font-weight:600">OVER</div></div>'
                f'<div style="background:#f5f3ff;border-radius:4px;padding:5px 1px"><div style="font-size:14px;font-weight:800;color:#7c3aed">{bk}</div><div style="font-size:7px;color:#94a3b8;font-weight:600">BLOCK</div></div>'
                f'</div>'
                f'<div style="font-size:9px;color:#94a3b8;font-weight:600;margin-bottom:3px">{cp}% COMPLETE</div>'
                f'<div style="background:#f1f5f9;border-radius:3px;height:5px;overflow:hidden">'
                f'<div style="width:{cp}%;height:100%;background:{cfg["color"]};border-radius:3px"></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"View {team.split()[0]} →", key=f"drill_{team}", use_container_width=True):
                st.session_state.update({"view": "team_detail", "selected_team": team})
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── NINE-BOX GRID ──
    with st.expander("🔲 Member Performance Nine-Box Grid — All Teams", expanded=True):
        render_nine_box(all_data)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── ITEMS OUT OF TRACK ──
    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:#94a3b8;letter-spacing:1.5px;'
        'text-transform:uppercase;margin-bottom:12px">🚨 Items Going Out of Track</div>',
        unsafe_allow_html=True
    )

    # Excel download — all teams
    excel_buf = build_excel(all_data)
    st.download_button(
        label="📥 Download All Teams — Excel",
        data=excel_buf,
        file_name=f"sprint_data_all_teams_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_all"
    )

    t1, t2, t3, t4 = st.tabs([
        f"⚠️ Spillover  ({len(spill_high)+len(spill_watch)})",
        f"🔥 Overburn  ({len(overs)})",
        f"🚧 Blocked  ({len(blocked_all)})",
        f"💀 Both Issues  ({len(both)})",
    ])
    with t1:
        items_s = sorted(spill_high + spill_watch, key=lambda x: 0 if x.get("spill_risk")=="high" else 1)
        if not items_s:
            st.success("✅ No spillover risk items across all teams")
        else:
            for i in items_s: item_card(i, all_data, "spill")
    with t2:
        items_o = sorted(overs, key=lambda x: x.get("overrun", 0), reverse=True)
        if not items_o:
            st.success("✅ No overburn items across all teams")
        else:
            for i in items_o: item_card(i, all_data, "overburn")
    with t3:
        if not blocked_all:
            st.success("✅ No externally blocked items")
        else:
            grouped = defaultdict(list)
            for item in blocked_all:
                for tag, cfg in item.get("blocked_tags", []):
                    grouped[tag].append((item, cfg))
            for tag, entries in grouped.items():
                tc = BLOCKED_TAGS.get(tag, BLOCKED_TAGS["Blocked"])
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;margin:14px 0 8px 0;'
                    f'padding:10px 14px;background:{tc["bg"]};border-radius:8px;border:1px solid {tc["border"]}">'
                    f'<span style="font-size:18px">{tc["icon"]}</span>'
                    f'<div><span style="font-size:13px;font-weight:700;color:{tc["color"]}">{tc["label"]}</span>'
                    f'<span style="background:{tc["bg"]};color:{tc["color"]};border:1px solid {tc["border"]};'
                    f'border-radius:4px;padding:1px 8px;font-size:10px;font-weight:700;margin-left:8px">{len(entries)} items</span>'
                    f'</div>'
                    f'<div style="margin-left:auto;text-align:right">'
                    f'<div style="font-size:10px;color:#64748b">Escalate to: <b style="color:#0f172a">{tc["owner"]}</b></div>'
                    f'<div style="font-size:10px;color:#94a3b8;font-style:italic">{tc["desc"]}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
                for item, _ in entries:
                    item_card(item, all_data, "blocked")
    with t4:
        if not both:
            st.success("✅ No items with both spillover and overburn")
        else:
            for i in sorted(both, key=lambda x: x.get("overrun", 0), reverse=True):
                item_card(i, all_data, "spill")

# ──────────────────────────────────────────────────────────────────
# VIEW 2: TEAM DETAIL
# ──────────────────────────────────────────────────────────────────
def render_team_detail(tdata, all_data):
    team     = tdata.get("team", "")
    health   = tdata.get("health", "no_data")
    cfg      = HEALTH_CFG[health]
    items    = tdata.get("items", [])
    av       = TEAM_AVATARS.get(team, "🔷")
    dl       = tdata.get("days_left", 0)
    ss       = tdata.get("sprint_start")
    se       = tdata.get("sprint_end")
    sn       = tdata.get("sprint_name", "—")
    tf       = tdata.get("timeframe", "current")
    dl_c     = "#dc2626" if dl <= 2 else "#ea580c" if dl <= 4 else "#475569"
    date_rng = f"{ss.strftime('%b %d') if ss else '—'} – {se.strftime('%b %d, %Y') if se else '—'}"

    cb, ch = st.columns([1, 10])
    with cb:
        if st.button("← Back", key="back_btn"):
            st.session_state["view"] = "alert_center"
            st.rerun()
    with ch:
        past_b = ' <span style="background:#fef3c7;color:#92400e;border:1px solid #fcd34d;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:700">📅 LAST SPRINT</span>' if tf == "past" else ""
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding:4px 0">'
            f'<span style="font-size:26px">{av}</span>'
            f'<div>'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'<span style="font-size:20px;font-weight:900;color:#0f172a">{team}</span>'
            f'{health_badge(health)}{past_b}'
            f'</div>'
            f'<div style="font-size:11px;color:#64748b;margin-top:2px">'
            f'{sn} &nbsp;·&nbsp; {date_rng} &nbsp;·&nbsp; '
            f'<b style="color:{dl_c}">{dl} working days left</b>'
            f'</div></div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # KPIs
    spill_h    = [i for i in items if i.get("spill_risk") == "high"]
    spill_w    = [i for i in items if i.get("spill_risk") == "watch"]
    overs      = [i for i in items if i.get("is_overburn")]
    blocked_t  = [i for i in items if i.get("is_blocked")]
    done_items = [i for i in items if i["state"] in COMPLETED]
    unest_items= [i for i in items if i.get("is_unestimated")]
    date_issue = [i for i in items if i.get("has_date_issue")]
    total_est  = sum(i.get("est", 0) or 0 for i in items)
    total_done = sum(i.get("done", 0) or 0 for i in items)
    total_rem  = sum(i.get("rem", 0) or 0 for i in items)

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    for col, (label, val, sub, color, bg) in zip([k1,k2,k3,k4,k5,k6], [
        ("Total Items",     len(items),              f"{len(done_items)} done",      "#2563eb","#eff6ff"),
        ("🔴 High Spill",   len(spill_h),            "likely to spill",              "#dc2626","#fef2f2"),
        ("🟡 Watch",        len(spill_w),            "needs attention",              "#ca8a04","#fefce8"),
        ("🔥 Overburn",     len(overs),              "over estimate",                "#ea580c","#fff7ed"),
        ("🚧 Blocked",      len(blocked_t),          f"🌩️{env_count(blocked_t)} 🔀{pr_count(blocked_t)} 🗄️{td_count(blocked_t)}","#7c3aed","#f5f3ff"),
        ("⚠️ Flags",        len(unest_items)+len(date_issue), f"{len(unest_items)} unest · {len(date_issue)} date","#be185d","#fdf2f8"),
    ]):
        col.markdown(
            f'<div style="background:{bg};border:1px solid {color}30;border-top:3px solid {color};'
            f'border-radius:8px;padding:12px;text-align:center">'
            f'<div style="font-size:9px;color:#64748b;letter-spacing:1px;font-weight:700;margin-bottom:4px">{label}</div>'
            f'<div style="font-size:26px;font-weight:900;color:{color};margin:2px 0">{val}</div>'
            f'<div style="font-size:9px;color:#94a3b8">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Hours summary
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:12px 20px;'
        f'margin-bottom:16px;display:flex;gap:32px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
        f'<div><span style="font-size:10px;color:#94a3b8;font-weight:600">ESTIMATED &nbsp;</span>'
        f'<span style="font-size:14px;font-weight:700;color:#0f172a">{total_est:.0f}h</span></div>'
        f'<div><span style="font-size:10px;color:#94a3b8;font-weight:600">LOGGED &nbsp;</span>'
        f'<span style="font-size:14px;font-weight:700;color:#16a34a">{total_done:.0f}h</span></div>'
        f'<div><span style="font-size:10px;color:#94a3b8;font-weight:600">REMAINING &nbsp;</span>'
        f'<span style="font-size:14px;font-weight:700;color:#ca8a04">{total_rem:.0f}h</span></div>'
        f'<div><span style="font-size:10px;color:#94a3b8;font-weight:600">COMPLETION &nbsp;</span>'
        f'<span style="font-size:14px;font-weight:700;color:#2563eb">{tdata.get("comp_pct",0)}%</span></div>'
        f'<div style="margin-left:auto">'
        f'<span style="font-size:10px;color:#94a3b8;font-weight:600">LAST UPDATED &nbsp;</span>'
        f'<span style="font-size:12px;font-weight:600;color:#475569">{datetime.now().strftime("%d %b %Y %H:%M")}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # Excel download — this team
    excel_buf = build_excel([tdata])
    st.download_button(
        label=f"📥 Download {team} Sprint Data — Excel",
        data=excel_buf,
        file_name=f"sprint_{team.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_team"
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Tabs
    tab1,tab2,tab3,tab4,tab5 = st.tabs([
        f"⚠️ Spillover ({len(spill_h)+len(spill_w)})",
        f"🔥 Overburn ({len(overs)})",
        f"🚧 Blocked ({len(blocked_t)})",
        f"👥 Member Load",
        f"📋 All Items ({len(items)})",
    ])

    with tab1:
        sorted_s = sorted(spill_h + spill_w, key=lambda x: 0 if x.get("spill_risk")=="high" else 1)
        if not sorted_s: st.success("✅ No spillover risk")
        else:
            for i in sorted_s: item_card(i, all_data, "spill")

    with tab2:
        sorted_o = sorted(overs, key=lambda x: x.get("overrun", 0), reverse=True)
        if not sorted_o: st.success("✅ No overburn items")
        else:
            for i in sorted_o: item_card(i, all_data, "overburn")

    with tab3:
        if not blocked_t: st.success("✅ No externally blocked items")
        else:
            grouped = defaultdict(list)
            for item in blocked_t:
                for tag, cfg2 in item.get("blocked_tags", []):
                    grouped[tag].append((item, cfg2))
            for tag, entries in grouped.items():
                tc = BLOCKED_TAGS.get(tag, BLOCKED_TAGS["Blocked"])
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;margin:12px 0 8px 0;'
                    f'padding:10px 14px;background:{tc["bg"]};border-radius:8px;border:1px solid {tc["border"]}">'
                    f'<span style="font-size:16px">{tc["icon"]}</span>'
                    f'<span style="font-size:13px;font-weight:700;color:{tc["color"]}">{tc["label"]}</span>'
                    f'<span style="font-size:10px;color:#64748b;margin-left:8px">→ <b>{tc["owner"]}</b></span>'
                    f'<span style="font-size:10px;color:#94a3b8;margin-left:8px;font-style:italic">{tc["desc"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                for item, _ in entries: item_card(item, all_data, "blocked")

    with tab4:
        render_member_load(items, all_data)

    with tab5:
        render_all_items(items)


def env_count(items): return sum(1 for i in items if any(t=="Env-Unstable"    for t,_ in i.get("blocked_tags",[])))
def pr_count(items):  return sum(1 for i in items if any(t=="PR-Approval"     for t,_ in i.get("blocked_tags",[])))
def td_count(items):  return sum(1 for i in items if any(t=="Test-Data-Issue" for t,_ in i.get("blocked_tags",[])))


def render_member_load(items, all_data):
    members = defaultdict(lambda: {"items":[],"done":0,"spill":0,"over":0,"block":0,"logged":0,"est":0})
    for item in items:
        a = item.get("assignee","Unassigned")
        members[a]["items"].append(item)
        if item["state"] in COMPLETED:                         members[a]["done"]  += 1
        if item.get("spill_risk") in ["high","watch"]:         members[a]["spill"] += 1
        if item.get("is_overburn"):                            members[a]["over"]  += 1
        if item.get("is_blocked"):                             members[a]["block"] += 1
        members[a]["logged"] += item.get("done", 0) or 0
        members[a]["est"]    += item.get("est",  0) or 0

    # Sort: most at risk first
    sorted_members = sorted(members.items(), key=lambda x: x[1]["spill"]*3 + x[1]["over"]*2 + x[1]["block"], reverse=True)
    cols = st.columns(min(len(sorted_members), 4))

    for idx, (name, data) in enumerate(sorted_members):
        col      = cols[idx % 4]
        total    = len(data["items"])
        pct      = int(data["done"] / total * 100) if total else 0
        bar_c    = "#16a34a" if pct >= 80 else "#ca8a04" if pct >= 50 else "#dc2626"
        init_str = initials(name)

        # Border: red if spill, purple if only blocked
        has_spill  = data["spill"] > 0
        has_block  = data["block"] > 0
        border_c   = "#dc2626" if has_spill else "#7c3aed" if has_block else "#e2e8f0"
        avatar_bg  = "#fef2f2" if has_spill else "#f5f3ff" if has_block else "#f1f5f9"
        avatar_c   = "#dc2626" if has_spill else "#7c3aed" if has_block else "#64748b"

        with col:
            st.markdown(
                f'<div style="background:#ffffff;border:2px solid {border_c};border-radius:10px;'
                f'padding:14px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.05)">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">'
                f'<div style="width:34px;height:34px;border-radius:50%;background:{avatar_bg};'
                f'border:2px solid {border_c};display:flex;align-items:center;justify-content:center;'
                f'font-size:11px;font-weight:800;color:{avatar_c}">{init_str}</div>'
                f'<div><div style="font-size:13px;font-weight:700;color:#0f172a">{name}</div>'
                f'<div style="font-size:9px;color:#94a3b8">{total} items &nbsp;·&nbsp; {data["logged"]:.0f}h logged</div>'
                f'</div></div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-bottom:10px;text-align:center">'
                f'<div style="background:#f0fdf4;border-radius:6px;padding:6px 2px">'
                f'<div style="font-size:16px;font-weight:800;color:#16a34a">{data["done"]}</div>'
                f'<div style="font-size:8px;color:#94a3b8;font-weight:600">DONE</div></div>'
                f'<div style="background:#fef2f2;border-radius:6px;padding:6px 2px">'
                f'<div style="font-size:16px;font-weight:800;color:#dc2626">{data["spill"]}</div>'
                f'<div style="font-size:8px;color:#94a3b8;font-weight:600">SPILL</div></div>'
                f'<div style="background:#fff7ed;border-radius:6px;padding:6px 2px">'
                f'<div style="font-size:16px;font-weight:800;color:#ea580c">{data["over"]}</div>'
                f'<div style="font-size:8px;color:#94a3b8;font-weight:600">OVER</div></div>'
                f'<div style="background:#f5f3ff;border-radius:6px;padding:6px 2px">'
                f'<div style="font-size:16px;font-weight:800;color:#7c3aed">{data["block"]}</div>'
                f'<div style="font-size:8px;color:#94a3b8;font-weight:600">BLOCK</div></div>'
                f'</div>'
                f'<div style="font-size:9px;color:#94a3b8;font-weight:600;margin-bottom:3px">{pct}% COMPLETE &nbsp;·&nbsp; {data["est"]:.0f}h estimated</div>'
                f'<div style="background:#f1f5f9;border-radius:3px;height:5px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{bar_c};border-radius:3px"></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )


def render_all_items(items):
    rows = []
    for i in items:
        sr  = i.get("spill_risk","none")
        ob  = i.get("is_overburn",False)
        bk  = i.get("is_blocked",False)
        un  = i.get("is_unestimated",False)
        di  = i.get("has_date_issue",False)
        flags = " ".join(filter(None,[
            "🔴 HIGH"  if sr=="high"  else "",
            "🟡 WATCH" if sr=="watch" else "",
            "🔥 OVER"  if ob          else "",
            "🚧 BLOCK" if bk          else "",
            "📋 UNEST" if un          else "",
            "📅 DATE"  if di          else "",
        ]))
        rows.append({
            "ID":         i.get("id"),
            "Type":       i.get("type",""),
            "Title":      (i["title"][:60]+"…") if len(i["title"])>60 else i["title"],
            "Assignee":   i.get("assignee","—").split()[0],
            "State":      i.get("state",""),
            "Est(h)":     i.get("est") or "—",
            "Done(h)":    i.get("done") or "—",
            "Rem(h)":     i.get("rem") or "—",
            "Flags":      flags or "✅",
            "Tags":       i.get("tags","")[:35],
            "Feature":    (i.get("feature_title","")[:40]+"…") if i.get("feature_title") and len(i.get("feature_title",""))>40 else i.get("feature_title","—"),
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=450)
    else:
        st.info("No items to display.")

# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────
def main():
    defaults = [
        ("view","alert_center"),("selected_team",TEAMS[0]),
        ("use_demo",True),("loaded",False),("all_data",[]),
        ("org_url","https://dev.azure.com/YOUR_ORG"),("project","HRM"),("pat",""),
    ]
    for k, v in defaults:
        if k not in st.session_state:
            st.session_state[k] = v

    render_sidebar()

    if not st.session_state["loaded"]:
        if st.session_state.get("use_demo"):
            with st.spinner("Loading demo data…"):
                st.session_state["all_data"] = gen_demo()
                st.session_state["loaded"]   = True
        elif st.session_state.get("pat"):
            prog     = st.progress(0, "Connecting to Azure DevOps…")
            all_data = []
            for idx, team in enumerate(TEAMS):
                prog.progress((idx+1)/len(TEAMS), f"Loading {team}…")
                all_data.append(load_team(
                    st.session_state["org_url"],
                    st.session_state["project"],
                    st.session_state["pat"],
                    team
                ))
            st.session_state["all_data"] = all_data
            st.session_state["loaded"]   = True
            prog.empty()
        else:
            st.markdown(
                '<div style="display:flex;flex-direction:column;align-items:center;'
                'justify-content:center;min-height:60vh;text-align:center">'
                '<div style="font-size:56px;margin-bottom:20px">🚨</div>'
                '<div style="font-size:28px;font-weight:900;color:#0f172a;margin-bottom:8px">Sprint Alert Center</div>'
                '<div style="font-size:14px;color:#64748b;max-width:400px;line-height:1.7">'
                'Connect your Azure DevOps via the sidebar,<br>'
                'or click <b style="color:#2563eb">Demo Data</b> to explore with sample data.'
                '</div></div>',
                unsafe_allow_html=True
            )
            return

    all_data = st.session_state["all_data"]
    view     = st.session_state["view"]

    if view == "alert_center":
        render_alert_center(all_data)
    elif view == "team_detail":
        sel   = st.session_state.get("selected_team", TEAMS[0])
        tdata = next((t for t in all_data if t["team"] == sel), None)
        if tdata:
            render_team_detail(tdata, all_data)
        else:
            st.session_state["view"] = "alert_center"
            st.rerun()

if __name__ == "__main__":
    main()
