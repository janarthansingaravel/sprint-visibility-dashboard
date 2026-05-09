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

st.set_page_config(
    page_title="Sprint Alert Center",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ──────────────────────────────────────────────────────────────────
# GLOBAL CSS  — readable, clean, leadership-grade
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #f0f4f8 !important;
    color: #1a202c !important;
    font-size: 15px !important;
}
.stApp { background: #f0f4f8; }
.block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
    box-shadow: 2px 0 8px rgba(0,0,0,0.06) !important;
}
[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
}
[data-testid="stSidebar"] input {
    font-size: 13px !important;
    color: #1a202c !important;
    background: #f7fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
}
[data-testid="stSidebar"] label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #718096 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* BUTTONS */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    transition: all 0.2s !important;
    border: 1.5px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #4a5568 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
}
.stButton > button:hover {
    border-color: #4299e1 !important;
    color: #2b6cb0 !important;
    background: #ebf8ff !important;
    box-shadow: 0 2px 6px rgba(66,153,225,0.2) !important;
}

/* TABS */
div[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #718096 !important;
    padding: 10px 16px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #2d3748 !important;
    font-weight: 700 !important;
}

/* DOWNLOAD BUTTON */
.stDownloadButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    background: #ebf8ff !important;
    color: #2b6cb0 !important;
    border: 1.5px solid #bee3f8 !important;
}

/* DATAFRAME */
.stDataFrame { border-radius: 10px !important; overflow: hidden !important; }

/* EXPANDER */
.streamlit-expanderHeader {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #2d3748 !important;
}

/* SCROLLBAR */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f0f4f8; }
::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 3px; }

/* SUCCESS / INFO */
.stSuccess, .stInfo { font-size: 14px !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────
TEAMS = ["Echo Engineers","Code Commanders","Beta Brigade","Gamma Guardians","Hyper Hackers"]
TEAM_AVATARS = {"Echo Engineers":"⚡","Code Commanders":"🛡️","Beta Brigade":"🔥","Gamma Guardians":"🌀","Hyper Hackers":"💥"}
TEAM_COLORS  = {"Echo Engineers":"#3b82f6","Code Commanders":"#8b5cf6","Beta Brigade":"#f97316","Gamma Guardians":"#10b981","Hyper Hackers":"#ec4899"}
COMPLETED    = ["Done","Resolved","Dev Completed"]
INPROGRESS   = ["In Progress","Scheduled"]
VALID_TYPES  = ["Task","Bug"]

HEALTH_CFG = {
    "critical":{"color":"#c53030","bg":"#fff5f5","border":"#fc8181","label":"CRITICAL","icon":"🔴"},
    "atrisk":  {"color":"#c05621","bg":"#fffaf0","border":"#f6ad55","label":"AT RISK",  "icon":"🟠"},
    "watch":   {"color":"#b7791f","bg":"#fffff0","border":"#f6e05e","label":"WATCH",    "icon":"🟡"},
    "healthy": {"color":"#276749","bg":"#f0fff4","border":"#68d391","label":"HEALTHY",  "icon":"🟢"},
    "no_data": {"color":"#4a5568","bg":"#f7fafc","border":"#cbd5e0","label":"NO DATA",  "icon":"⚫"},
}

BLOCKED_TAGS = {
    "Env-Unstable":    {"label":"Environment Unstable", "icon":"🌩️","color":"#6b21a8","bg":"#f5f3ff","border":"#c4b5fd","owner":"DevOps Team",    "desc":"Environment unstable — cannot test/deploy"},
    "PR-Approval":     {"label":"PR Awaiting Approval", "icon":"🔀","color":"#1e40af","bg":"#eff6ff","border":"#93c5fd","owner":"Tech Lead / Peer","desc":"Pull request waiting for code review"},
    "Test-Data-Issue": {"label":"Test Data Issue",      "icon":"🗄️","color":"#9a3412","bg":"#fff7ed","border":"#fdba74","owner":"BA / QA Lead",   "desc":"Missing or incorrect test data"},
    "Blocked":         {"label":"Blocked",              "icon":"🚧","color":"#991b1b","bg":"#fef2f2","border":"#fca5a5","owner":"Scrum Master",   "desc":"Blocked — escalation required"},
}

FLAG_COLORS = {
    "spill_high":    {"color":"#c53030","bg":"#fff5f5","border":"#fc8181","label":"🔴 HIGH RISK"},
    "spill_watch":   {"color":"#b7791f","bg":"#fffff0","border":"#f6e05e","label":"🟡 WATCH"},
    "overburn":      {"color":"#c05621","bg":"#fffaf0","border":"#f6ad55","label":"🔥 OVERBURN"},
    "blocked":       {"color":"#6b21a8","bg":"#f5f3ff","border":"#c4b5fd","label":"🚧 BLOCKED"},
    "unestimated":   {"color":"#0e7490","bg":"#ecfeff","border":"#67e8f9","label":"📋 NO ESTIMATE"},
    "date_violation":{"color":"#9d174d","bg":"#fdf2f8","border":"#f9a8d4","label":"📅 DATE ISSUE"},
}

# ──────────────────────────────────────────────────────────────────
# AZURE DEVOPS CLIENT
# ──────────────────────────────────────────────────────────────────
class DevOpsClient:
    def __init__(self, org, proj, pat):
        self.org  = org.rstrip("/")
        self.proj = proj
        tok       = base64.b64encode(f":{pat}".encode()).decode()
        self.h    = {"Authorization":f"Basic {tok}","Content-Type":"application/json"}

    def _get(self, url, params=None):
        try:
            r = requests.get(url, headers=self.h, params=params, timeout=20)
            r.raise_for_status(); return r.json()
        except: return None

    def _post(self, url, body):
        try:
            r = requests.post(url, headers=self.h, json=body, timeout=20)
            r.raise_for_status(); return r.json()
        except: return None

    def get_sprint(self, team):
        base = f"{self.org}/{self.proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations"
        d = self._get(base, {"$timeframe":"current","api-version":"7.0"})
        if d and d.get("value"):
            sp = d["value"][0]; sp["_timeframe"] = "current"; return sp
        d = self._get(base, {"$timeframe":"past","api-version":"7.0"})
        if d and d.get("value"):
            sprints = sorted(d["value"], key=lambda x: x.get("attributes",{}).get("finishDate",""), reverse=True)
            sp = sprints[0]; sp["_timeframe"] = "past"; return sp
        return None

    def get_wi_ids(self, team, iid):
        url  = f"{self.org}/{self.proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations/{iid}/workitems"
        data = self._get(url, {"api-version":"7.0"})
        if not data: return []
        ids = []
        for wi in data.get("workItemRelations",[]):
            try:
                t = wi.get("target")
                if t and t.get("id"): ids.append(t["id"])
            except: continue
        return list(set(ids))

    def get_wi_batch(self, ids):
        if not ids: return []
        fields = ["System.Id","System.Title","System.WorkItemType","System.State","System.AssignedTo",
                  "System.Parent","Microsoft.VSTS.Scheduling.OriginalEstimate",
                  "Microsoft.VSTS.Scheduling.CompletedWork","Microsoft.VSTS.Scheduling.RemainingWork",
                  "Microsoft.VSTS.Common.Priority","Microsoft.VSTS.Common.Activity","System.Tags",
                  "Microsoft.VSTS.Scheduling.StartDate","Microsoft.VSTS.Scheduling.TargetDate"]
        out = []
        for i in range(0, len(ids), 200):
            d = self._post(f"{self.org}/_apis/wit/workitemsbatch?api-version=7.0",
                           {"ids":ids[i:i+200],"fields":fields})
            if d: out.extend(d.get("value",[]))
        return out

# ──────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────
def whl(end):
    if not end: return 0
    today = date.today()
    if today > end: return 0
    c=0; cur=today
    while cur <= end:
        if cur.weekday()<5: c+=1
        cur=date.fromordinal(cur.toordinal()+1)
    return c*8

def wdl(end):
    if not end: return 0
    today=date.today()
    if today>end: return 0
    c=0; cur=today
    while cur<=end:
        if cur.weekday()<5: c+=1
        cur=date.fromordinal(cur.toordinal()+1)
    return c

def pdate(v):
    if not v: return None
    try: return datetime.strptime(str(v)[:10],"%Y-%m-%d").date()
    except: return None

def inits(name):
    p=str(name).split()
    return "".join(x[0] for x in p[:2]).upper() if p else "?"

def detect_blocked(tags):
    if not tags: return []
    tlist=[t.strip() for t in str(tags).split(";")]
    matched=[]
    if "Blocked" in tlist:
        for sub in ["Env-Unstable","PR-Approval","Test-Data-Issue"]:
            if sub in tlist: matched.append((sub,BLOCKED_TAGS[sub]))
        if not matched: matched.append(("Blocked",BLOCKED_TAGS["Blocked"]))
    return matched

def check_dates(is_, it, ss, se):
    v=[]
    if not is_: v.append("Start date not set")
    elif ss and is_<ss: v.append(f"Start {is_.strftime('%b %d')} before sprint")
    elif se and is_>se: v.append(f"Start {is_.strftime('%b %d')} after sprint")
    if not it: v.append("Target date not set")
    elif se and it>se: v.append(f"Target {it.strftime('%b %d')} beyond sprint end")
    return v

def classify_spill(item, hl):
    state=item.get("state",""); est=item.get("est",0) or 0
    done=item.get("done",0) or 0; rem=item.get("rem",0) or 0
    if state in COMPLETED: return "none",[]
    is_ip=state in INPROGRESS; is_todo=state=="To Do"; is_hold=state=="On hold"
    total=done+rem; prog=(done/total) if total>0 else 0
    risk="none"; reasons=[]
    if is_hold:                              risk="high"; reasons.append("Blocked — On Hold")
    if is_todo and rem>hl and hl>0:          risk="high"; reasons.append(f"Not started · {rem}h needed, {hl}h left")
    if state=="Scheduled" and rem>hl and hl>0: risk="high"; reasons.append(f"Scheduled · {rem}h rem > {hl}h left")
    td=item.get("target_date"); se=item.get("sprint_end")
    if td and se and td>se:                  risk="high"; reasons.append(f"Target {td.strftime('%b %d')} past sprint end")
    if risk!="high":
        if is_todo and 0<rem<=hl and rem>4:  risk="watch"; reasons.append(f"Not started · {rem}h remaining")
        if is_ip and total>4 and prog<0.3:   risk="watch"; reasons.append(f"Only {int(prog*100)}% done ({done}h of {total}h)")
        if is_ip and done==0 and rem>0:      risk="watch"; reasons.append("In Progress — 0 hours logged")
        if state=="Scheduled":               risk="watch"; reasons.append("Scheduled — not activated")
        if is_ip and hl>0 and rem>(hl*0.8): risk="watch"; reasons.append(f"{rem}h rem with limited time")
    return risk,reasons

def classify_overburn(item):
    state=item.get("state",""); est=item.get("est",0) or 0
    done=item.get("done",0) or 0; rem=item.get("rem",0) or 0
    if est<=0: return False,0,done
    if state in COMPLETED:
        ov=done-est; return ov>0,round(max(ov,0),1),round(done,1)
    elif state in INPROGRESS:
        proj=done+rem; ov=proj-est; return ov>0,round(max(ov,0),1),round(proj,1)
    return False,0,done

def member_risk_score(items):
    s=sum(3 if i.get("spill_risk")=="high" else 1 if i.get("spill_risk")=="watch" else 0 for i in items)
    o=sum(2 for i in items if i.get("is_overburn"))
    b=sum(1 for i in items if i.get("is_blocked"))
    return s+o+b

def compute_health(items):
    tasks=[i for i in items if i.get("type") in VALID_TYPES] or items
    total=len(tasks); done_c=sum(1 for i in tasks if i["state"] in COMPLETED)
    hc=sum(1 for i in tasks if i.get("spill_risk")=="high")
    wc=sum(1 for i in tasks if i.get("spill_risk")=="watch")
    oc=sum(1 for i in tasks if i.get("is_overburn"))
    bc=sum(1 for i in tasks if i.get("is_blocked"))
    cp=round(done_c/total*100) if total else 0; op=round(oc/total*100) if total else 0
    if hc>=3 or op>=30 or bc>=3: h="critical"
    elif hc>=1 or op>=15 or bc>=1: h="atrisk"
    elif wc>=1 or oc>0: h="watch"
    else: h="healthy"
    return {"health":h,"total":total,"done_count":done_c,"high_count":hc,
            "watch_count":wc,"over_count":oc,"blocked_count":bc,"comp_pct":cp}

# ──────────────────────────────────────────────────────────────────
# DATA LOADER
# ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_team(org, proj, pat, team):
    cl=DevOpsClient(org,proj,pat)
    sp=cl.get_sprint(team)
    if not sp:
        return {"team":team,"error":"No sprint found","items":[],"health":"no_data",
                "total":0,"done_count":0,"high_count":0,"watch_count":0,"over_count":0,"blocked_count":0,"comp_pct":0}
    attrs=sp.get("attributes",{}); sname=sp.get("name",""); tf=sp.get("_timeframe","current")
    ss=pdate(attrs.get("startDate")); se=pdate(attrs.get("finishDate"))
    hl=whl(se); dl=wdl(se)
    ids=cl.get_wi_ids(team,sp.get("id",""))
    if not ids:
        h=compute_health([])
        return {"team":team,"sprint_name":sname,"timeframe":tf,"sprint_start":ss,"sprint_end":se,
                "hrs_left":hl,"days_left":dl,"items":[],"error":None,**h}
    raw=cl.get_wi_batch(ids); pids=set(); items=[]
    for wi in raw:
        f=wi.get("fields",{})
        wt=f.get("System.WorkItemType","")
        if wt not in VALID_TYPES: continue
        af=f.get("System.AssignedTo",{})
        assignee=af.get("displayName","Unassigned") if isinstance(af,dict) else str(af or "Unassigned")
        pid=f.get("System.Parent")
        if pid: pids.add(pid)
        tags=f.get("System.Tags","") or ""
        is_=pdate(f.get("Microsoft.VSTS.Scheduling.StartDate"))
        it=pdate(f.get("Microsoft.VSTS.Scheduling.TargetDate"))
        item={"id":wi.get("id"),"title":f.get("System.Title",""),"type":wt,
              "state":f.get("System.State",""),"assignee":assignee,
              "est":f.get("Microsoft.VSTS.Scheduling.OriginalEstimate") or 0,
              "done":f.get("Microsoft.VSTS.Scheduling.CompletedWork") or 0,
              "rem":f.get("Microsoft.VSTS.Scheduling.RemainingWork") or 0,
              "priority":f.get("Microsoft.VSTS.Common.Priority",3),
              "activity":f.get("Microsoft.VSTS.Common.Activity",""),
              "tags":tags,"item_start":is_,"item_target":it,"parent_id":pid,
              "sprint_name":sname,"sprint_start":ss,"sprint_end":se,"team":team,"timeframe":tf,
              "devops_url":f"{org}/{proj}/_workitems/edit/{wi.get('id')}",
              "backlog_title":"","backlog_url":"#","feature_title":"","feature_url":"#"}
        sr,rr=classify_spill(item,hl); iso,ov,pj=classify_overburn(item)
        bt=detect_blocked(tags); dv=check_dates(is_,it,ss,se)
        item.update({"spill_risk":sr,"spill_reasons":rr,"is_overburn":iso,"overrun":ov,
                     "projected":pj,"blocked_tags":bt,"is_blocked":len(bt)>0,
                     "date_violations":dv,"has_date_issue":len(dv)>0,
                     "is_unestimated":(item["est"] or 0)==0 and item["state"] not in COMPLETED})
        items.append(item)
    if pids:
        parents=cl.get_wi_batch(list(pids)); gids=set(); pmap={}
        for p in parents:
            f=p.get("fields",{}); pid2=p.get("id")
            pmap[pid2]={"title":f.get("System.Title",""),"parent_id":f.get("System.Parent"),
                        "url":f"{org}/{proj}/_workitems/edit/{pid2}"}
            if f.get("System.Parent"): gids.add(f["System.Parent"])
        gpmap={}
        if gids:
            for gp in cl.get_wi_batch(list(gids)):
                f=gp.get("fields",{}); gpid=gp.get("id")
                gpmap[gpid]={"title":f.get("System.Title",""),"url":f"{org}/{proj}/_workitems/edit/{gpid}"}
        for item in items:
            pid=item.get("parent_id")
            if pid and pid in pmap:
                item["backlog_title"]=pmap[pid]["title"]; item["backlog_url"]=pmap[pid]["url"]
                gpid=pmap[pid].get("parent_id")
                if gpid and gpid in gpmap:
                    item["feature_title"]=gpmap[gpid]["title"]; item["feature_url"]=gpmap[gpid]["url"]
    h=compute_health(items)
    return {"team":team,"sprint_name":sname,"timeframe":tf,"sprint_start":ss,"sprint_end":se,
            "hrs_left":hl,"days_left":dl,"items":items,"error":None,**h}

# ──────────────────────────────────────────────────────────────────
# DEMO DATA
# ──────────────────────────────────────────────────────────────────
def gen_demo():
    from random import seed,randint,choice,random,uniform
    seed(42)
    today=date.today()
    cfgs={"Echo Engineers":  {"h":3,"w":4,"o":5,"b":2,"dp":0.42,"ss":date(2026,5,4),"se":date(2026,5,15)},
          "Code Commanders": {"h":1,"w":3,"o":3,"b":1,"dp":0.60,"ss":date(2026,5,4),"se":date(2026,5,15)},
          "Beta Brigade":    {"h":2,"w":2,"o":4,"b":2,"dp":0.48,"ss":date(2026,4,27),"se":date(2026,5,8)},
          "Gamma Guardians": {"h":0,"w":2,"o":2,"b":0,"dp":0.72,"ss":date(2026,5,4),"se":date(2026,5,15)},
          "Hyper Hackers":   {"h":0,"w":0,"o":0,"b":0,"dp":0.90,"ss":date(2026,4,27),"se":date(2026,5,8)}}
    feats=["Employee Info Module v2","Payroll Engine","Leave Management","Performance Portal","Recruitment Flow"]
    bls=["API Layer Implementation","Test Coverage","UI Revamp","Data Migration","Integration Testing","Documentation"]
    mems={"Echo Engineers":["Amila F.","Chamod B.","Hansani G.","Sharini N.","Udara W.","Luqman R."],
          "Code Commanders":["Kasun B.","Praveena G.","Nadith L.","Michelle P.","Iran U.","Maksudul R."],
          "Beta Brigade":["Sammani E.","Mihirani G.","Liyathambara G.","Alex K.","Priya M.","Suresh T."],
          "Gamma Guardians":["Nadia R.","Chen W.","Omar B.","Tara L.","Dev S.","Kim H."],
          "Hyper Hackers":["Raj P.","Fatima A.","Tom B.","Sara L.","Mei X.","Janaka K."]}
    btags=["Blocked; Env-Unstable","Blocked; PR-Approval","Blocked; Test-Data-Issue"]
    all_data=[]; iid=130000
    for team,cfg in cfgs.items():
        items=[]; n=randint(20,30); tm=mems[team]
        ss=cfg["ss"]; se=cfg["se"]; hl=whl(se); dl=wdl(se)
        tf="current" if today<=se else "past"
        sp_name=f"26R1_SP{'06' if tf=='current' else '05'}"
        for j in range(n):
            iid+=1; feat=feats[j%5]; bl=bls[j%6]; mem=tm[j%len(tm)]
            is_h=j<cfg["h"]; is_w=cfg["h"]<=j<cfg["h"]+cfg["w"]; is_o=j<cfg["o"]; is_b=j<cfg["b"]
            is_d=random()<cfg["dp"]
            if is_d:   state=choice(["Done","Done","Resolved","Dev Completed"])
            elif is_h: state=choice(["To Do","On hold","Scheduled"])
            elif is_w: state=choice(["In Progress","To Do"])
            else:      state=choice(["To Do","In Progress","Done"])
            est=round(randint(2,16)*0.5,1) if j%8!=0 else 0
            if state in COMPLETED:
                dh=round(est*(1.3 if is_o else uniform(0.7,1.0)),1) if est>0 else round(uniform(1,8),1); rh=0
            elif state=="In Progress":
                dh=round(est*uniform(0.1,0.5),1) if est>0 else 0
                rh=round((est*1.4-dh) if is_o else max(est-dh+uniform(0,2),0),1) if est>0 else round(uniform(2,8),1)
            else:
                dh=0; rh=est if not is_h else round(est+randint(8,20),1)
            tags=choice(btags) if (is_b and state not in COMPLETED) else "26R1"
            is_=ss if j%10!=0 else None
            it=se if j%10!=0 and j%13!=0 else (date(2026,5,30) if j%13==0 else None)
            item={"id":iid,"title":f"[{'DEV' if j%3==0 else 'QA' if j%3==1 else 'BA'}] {bl} — {feat[:35]}",
                  "type":choice(["Task","Task","Task","Bug"]),"state":state,"assignee":mem,
                  "est":est,"done":round(dh,1),"rem":round(max(rh,0),1),
                  "priority":randint(1,3),"activity":choice(["Development","Testing","Documentation"]),
                  "tags":tags,"item_start":is_,"item_target":it,"parent_id":120000+j,
                  "sprint_name":sp_name,"sprint_start":ss,"sprint_end":se,"team":team,"timeframe":tf,
                  "devops_url":f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{iid}",
                  "backlog_title":bl,"backlog_url":f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{120000+j}",
                  "feature_title":feat,"feature_url":f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{110000+(j%5)}"}
            sr,rr=classify_spill(item,hl); iso,ov,pj=classify_overburn(item)
            bt=detect_blocked(tags); dv=check_dates(is_,it,ss,se)
            item.update({"spill_risk":sr,"spill_reasons":rr,"is_overburn":iso,"overrun":ov,
                         "projected":pj,"blocked_tags":bt,"is_blocked":len(bt)>0,
                         "date_violations":dv,"has_date_issue":len(dv)>0,
                         "is_unestimated":(est or 0)==0 and state not in COMPLETED})
            items.append(item)
        h=compute_health(items)
        all_data.append({"team":team,"sprint_name":sp_name,"timeframe":tf,"sprint_start":ss,
                         "sprint_end":se,"hrs_left":hl,"days_left":dl,"items":items,"error":None,**h})
    return all_data

# ──────────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ──────────────────────────────────────────────────────────────────
def build_excel(all_data):
    rows=[]
    for t in all_data:
        for i in t.get("items",[]):
            rows.append({"Work Item ID":i.get("id"),"Title":i.get("title",""),"Type":i.get("type",""),
                "State":i.get("state",""),"Assigned To":i.get("assignee",""),"Team":t.get("team",""),
                "Sprint":i.get("sprint_name",""),"Sprint Start":str(i.get("sprint_start","")),
                "Sprint End":str(i.get("sprint_end","")),"Original Est (h)":i.get("est",0),
                "Completed (h)":i.get("done",0),"Remaining (h)":i.get("rem",0),"Projected (h)":i.get("projected",0),
                "Spill Risk":i.get("spill_risk","none").upper(),"Spill Reasons":" | ".join(i.get("spill_reasons",[])),
                "Is Overburn":"YES" if i.get("is_overburn") else "NO","Overrun (h)":i.get("overrun",0),
                "Is Blocked":"YES" if i.get("is_blocked") else "NO","Blocked Tags":i.get("tags",""),
                "Is Unestimated":"YES" if i.get("is_unestimated") else "NO",
                "Date Violation":"YES" if i.get("has_date_issue") else "NO",
                "Date Issues":" | ".join(i.get("date_violations",[])),
                "Item Start":str(i.get("item_start","")),"Item Target":str(i.get("item_target","")),
                "Feature":i.get("feature_title",""),"Backlog Item":i.get("backlog_title",""),
                "DevOps URL":i.get("devops_url","")})
    df=pd.DataFrame(rows); buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as w:
        df.to_excel(w,index=False,sheet_name="Sprint Data")
        ws=w.sheets["Sprint Data"]
        for col in ws.columns:
            ml=max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[col[0].column_letter].width=min(ml+4,60)
    buf.seek(0); return buf

# ──────────────────────────────────────────────────────────────────
# UI HELPERS
# ──────────────────────────────────────────────────────────────────
def fpill(key):
    c=FLAG_COLORS.get(key,{})
    return (f'<span style="background:{c.get("bg","#f7fafc")};color:{c.get("color","#4a5568")};'
            f'border:1px solid {c.get("border","#e2e8f0")};border-radius:6px;padding:3px 10px;'
            f'font-size:12px;font-weight:600;white-space:nowrap">{c.get("label","?")}</span>')

def hbadge(status, size=13):
    c=HEALTH_CFG.get(status,HEALTH_CFG["no_data"])
    return (f'<span style="background:{c["bg"]};color:{c["color"]};border:1px solid {c["border"]};'
            f'border-radius:6px;padding:3px 12px;font-size:{size}px;font-weight:700">{c["icon"]} {c["label"]}</span>')

def item_card(item, all_data, mode="spill"):
    team=item.get("team",""); tc=TEAM_COLORS.get(team,"#718096")
    sr=item.get("spill_risk","none"); iso=item.get("is_overburn",False)
    is_b=item.get("is_blocked",False); un=item.get("is_unestimated",False); di=item.get("has_date_issue",False)
    if mode=="spill":      bc="#c53030" if sr=="high" else "#b7791f"
    elif mode=="overburn":
        pct2=int(item.get("projected",0)/item.get("est",1)*100) if item.get("est",0)>0 else 0
        bc="#c53030" if pct2>=150 else "#c05621"
    elif mode=="blocked":
        first=item.get("blocked_tags",[("Blocked",BLOCKED_TAGS["Blocked"])])[0]
        bc=BLOCKED_TAGS.get(first[0],BLOCKED_TAGS["Blocked"])["color"]
    else: bc="#718096"
    pills=[]
    if sr=="high":   pills.append(fpill("spill_high"))
    elif sr=="watch":pills.append(fpill("spill_watch"))
    if iso:          pills.append(fpill("overburn"))
    if is_b:         pills.append(fpill("blocked"))
    if un:           pills.append(fpill("unestimated"))
    if di:           pills.append(fpill("date_violation"))
    ph=" ".join(pills)
    bl_h=(f'<a href="{item.get("backlog_url","#")}" target="_blank" style="color:#718096;font-size:13px;text-decoration:none">{item.get("backlog_title","")[:40]}</a>' if item.get("backlog_title") else "")
    ft_h=(f'<a href="{item.get("feature_url","#")}" target="_blank" style="color:#2b6cb0;font-size:13px;font-weight:600;text-decoration:none">📌 {item.get("feature_title","")[:45]}</a>' if item.get("feature_title") else "")
    bc2=" › ".join(filter(None,[bl_h,ft_h]))
    if mode=="spill":      detail=" · ".join(item.get("spill_reasons",[]))
    elif mode=="overburn":
        est=item.get("est",0); proj=item.get("projected",0); ov=item.get("overrun",0)
        is_ip=item.get("state") in INPROGRESS
        pct3=int(proj/est*100) if est>0 else 0
        detail=f"Est: {est}h → {'Projected' if is_ip else 'Actual'}: {proj:.1f}h · Overrun: +{ov:.1f}h ({pct3}%)"
    elif mode=="blocked":
        detail=" | ".join(f'{cfg["icon"]} {cfg["label"]} → {cfg["owner"]}' for _,cfg in item.get("blocked_tags",[]))
    else: detail=""
    past_b=('<span style="background:#fefcbf;color:#744210;border:1px solid #f6e05e;border-radius:4px;'
            'padding:2px 8px;font-size:11px;font-weight:700;margin-left:6px">📅 LAST SPRINT</span>'
            if item.get("timeframe")=="past" else "")
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:5px solid {bc};'
        f'border-radius:10px;padding:16px 20px;margin-bottom:10px;box-shadow:0 2px 4px rgba(0,0,0,0.06)">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px">'
        f'<div style="flex:1;min-width:0">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap">'
        f'<a href="{item.get("devops_url","#")}" target="_blank" style="color:#2b6cb0;font-family:monospace;'
        f'font-size:13px;font-weight:700;text-decoration:none;background:#ebf8ff;padding:2px 8px;border-radius:4px">#{item["id"]}</a>'
        f'{past_b}'
        f'<span style="color:#1a202c;font-size:15px;font-weight:600">{item["title"][:70]}{"…" if len(item["title"])>70 else ""}</span>'
        f'</div>'
        f'<div style="font-size:13px;color:#718096;margin-bottom:8px">'
        f'<span style="color:{tc};font-weight:600">{team}</span>'
        f'{(" › "+bc2) if bc2 else ""}'
        f'</div>'
        f'<div style="font-size:13px;color:#4a5568;font-style:italic;margin-bottom:8px">⚡ {detail}</div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap">{ph}</div>'
        f'</div>'
        f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;flex-shrink:0;min-width:110px">'
        f'<span style="font-size:14px;color:#2d3748;font-weight:600">{item.get("assignee","—")}</span>'
        f'<span style="background:#f7fafc;color:#4a5568;border:1px solid #e2e8f0;border-radius:6px;'
        f'padding:2px 10px;font-size:12px;font-weight:500">{item.get("state","—")}</span>'
        f'<span style="font-size:13px;color:#b7791f;font-weight:600">{item.get("rem",0)}h remaining</span>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

# ──────────────────────────────────────────────────────────────────
# NINE-BOX GRID  — catchy, bold, impactful
# ──────────────────────────────────────────────────────────────────
def render_nine_box(all_data):
    members=defaultdict(lambda:{"items":[],"team":""})
    for t in all_data:
        for i in t.get("items",[]):
            a=i.get("assignee","Unassigned")
            members[a]["items"].append(i); members[a]["team"]=t.get("team","")

    dots=[]
    for name,data in members.items():
        items=data["items"]; team=data["team"]
        if not items: continue
        total=len(items); done_c=sum(1 for i in items if i["state"] in COMPLETED)
        comp=round(done_c/total*100); rsc=member_risk_score(items)
        est_h=sum(i.get("est",0) or 0 for i in items)
        sh=sum(1 for i in items if i.get("spill_risk")=="high")
        sw=sum(1 for i in items if i.get("spill_risk")=="watch")
        oc=sum(1 for i in items if i.get("is_overburn"))
        bc=sum(1 for i in items if i.get("is_blocked"))
        risk_n=min(rsc*5,100)
        dot_sz=max(24,min(est_h*1.8,52))
        # Color by dominant issue
        if sh>0:             dc="#c53030"
        elif oc>0 and bc>0:  dc="#6b21a8"
        elif oc>0:           dc="#c05621"
        elif bc>0:           dc="#6b21a8"
        elif sw>0:           dc="#b7791f"
        else:                dc="#276749"
        in_crit=risk_n>60 and comp<40
        label=name.split()[0] if in_crit else inits(name)
        dots.append({"name":name,"team":team,"x":comp,"y":risk_n,"sz":dot_sz,"dc":dc,
                     "label":label,"crit":in_crit,"comp":comp,"rsc":rsc,
                     "sh":sh,"sw":sw,"oc":oc,"bc":bc,"total":total,"est_h":est_h,"has_b":bc>0})

    if not dots: st.info("No member data available."); return

    fig=go.Figure()

    # Bold quadrant backgrounds
    quad_defs=[
        (0,66,40,100,"#fff5f5","🔴 CRITICAL",      "#c53030"),
        (40,66,75,100,"#fffaf0","🔥 OVERLOADED",    "#c05621"),
        (75,66,100,100,"#fffff0","⚡ STRETCHED",     "#b7791f"),
        (0,33,40,66, "#fffaf0","⚠️ STRUGGLING",     "#c05621"),
        (40,33,75,66, "#fffff0","👁 WATCH",          "#b7791f"),
        (75,33,100,66,"#f0fff4","📈 ON TRACK",       "#276749"),
        (0,0,40,33,  "#fffff0","🐢 SLOW START",      "#b7791f"),
        (40,0,75,33, "#f0fff4","✅ DELIVERING",      "#276749"),
        (75,0,100,33,"#f0fff4","⭐ STAR",            "#276749"),
    ]
    for x0,y0,x1,y1,bg,lbl,lc in quad_defs:
        fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,
                      fillcolor=bg,line=dict(color="#e2e8f0",width=1.5))
        fig.add_annotation(x=(x0+x1)/2,y=y1-4,text=f"<b>{lbl}</b>",
                           font=dict(size=11,color=lc),showarrow=False,
                           xanchor="center",yanchor="top")

    # Dividers
    for v in [40,75]:
        fig.add_shape(type="line",x0=v,y0=0,x1=v,y1=100,
                      line=dict(color="#cbd5e0",width=1.5,dash="dash"))
    for h in [33,66]:
        fig.add_shape(type="line",x0=0,y0=h,x1=100,y1=h,
                      line=dict(color="#cbd5e0",width=1.5,dash="dash"))

    # Axis labels
    for x,lbl in [(20,"LOW"),(57,"MEDIUM"),(87,"HIGH")]:
        fig.add_annotation(x=x,y=-8,text=f"<b>{lbl} DELIVERY</b>",
                           font=dict(size=10,color="#718096"),showarrow=False,xanchor="center")
    for y,lbl in [(16,"LOW RISK"),(50,"MED RISK"),(83,"HIGH RISK")]:
        fig.add_annotation(x=-8,y=y,text=f"<b>{lbl}</b>",
                           font=dict(size=10,color="#718096"),showarrow=False,
                           xanchor="right",textangle=-90)

    # Purple blocked ring
    for d in [x for x in dots if x["has_b"]]:
        fig.add_trace(go.Scatter(x=[d["x"]],y=[d["y"]],mode="markers",
                                 marker=dict(size=d["sz"]+14,color="rgba(107,33,168,0.15)",
                                             line=dict(color="#6b21a8",width=3)),
                                 showlegend=False,hoverinfo="skip"))

    # Team color ring
    for d in dots:
        tc=TEAM_COLORS.get(d["team"],"#718096")
        fig.add_trace(go.Scatter(x=[d["x"]],y=[d["y"]],mode="markers",
                                 marker=dict(size=d["sz"]+6,color="rgba(255,255,255,0.8)",
                                             line=dict(color=tc,width=3)),
                                 showlegend=False,hoverinfo="skip"))

    # Main dots with labels
    for d in dots:
        fig.add_trace(go.Scatter(
            x=[d["x"]],y=[d["y"]],mode="markers+text",
            marker=dict(size=d["sz"],color=d["dc"],
                        line=dict(color="rgba(255,255,255,0.8)",width=2),opacity=0.92),
            text=f"<b>{d['label']}</b>",textposition="middle center",
            textfont=dict(size=10 if d["crit"] else 9,color="#ffffff"),
            hovertemplate=(
                f"<b style='font-size:14px'>{d['name']}</b><br>"
                f"<b>Team:</b> {d['team']}<br>"
                f"<b>Completion:</b> {d['comp']}%<br>"
                f"<b>Risk Score:</b> {d['rsc']}<br>"
                f"━━━━━━━━━━━━━━<br>"
                f"🔴 High Spill: {d['sh']} &nbsp; 🟡 Watch: {d['sw']}<br>"
                f"🔥 Overburn: {d['oc']} &nbsp; 🚧 Blocked: {d['bc']}<br>"
                f"━━━━━━━━━━━━━━<br>"
                f"📋 Total Items: {d['total']}<br>"
                f"⏱️ Est Hours: {d['est_h']:.0f}h"
                "<extra></extra>"
            ),
            showlegend=False,name=d["name"]
        ))

    # Pulsing effect for critical dots — add outer glow
    crit_dots=[d for d in dots if d["crit"]]
    if crit_dots:
        fig.add_trace(go.Scatter(
            x=[d["x"] for d in crit_dots],y=[d["y"] for d in crit_dots],mode="markers",
            marker=dict(size=[d["sz"]+22 for d in crit_dots],
                        color=["rgba(197,48,48,0.12)" for _ in crit_dots],
                        line=dict(color="#c53030",width=2)),
            showlegend=False,hoverinfo="skip",name="critical_glow"
        ))

    fig.update_layout(
        height=500,margin=dict(l=60,r=20,t=60,b=60),
        plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
        title_text="<b>Member Performance Nine-Box · All Teams</b>",
        title_x=0.01,
        xaxis=dict(range=[-5,105],showgrid=False,zeroline=False,
                   showticklabels=False,title=""),
        yaxis=dict(range=[-10,105],showgrid=False,zeroline=False,
                   showticklabels=False,title=""),
    )

    st.plotly_chart(fig,use_container_width=True)

    # Legend row
    legend=[("🔴 High Spill","#c53030"),("🔥 Overburn","#c05621"),
            ("🟡 Watch","#b7791f"),("🟢 Clean","#276749"),("🟣 Blocked (ring)","#6b21a8")]
    cols=st.columns(len(legend)+1)
    cols[0].markdown('<div style="font-size:13px;color:#718096;font-weight:600;padding-top:4px">Dot colour:</div>',unsafe_allow_html=True)
    for col,(lbl,color) in zip(cols[1:],legend):
        col.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:13px;color:#4a5568">'
            f'<div style="width:14px;height:14px;border-radius:50%;background:{color}"></div>{lbl}</div>',
            unsafe_allow_html=True)

    # Team color legend
    cols2=st.columns(len(TEAM_COLORS)+1)
    cols2[0].markdown('<div style="font-size:13px;color:#718096;font-weight:600;padding-top:4px">Ring = Team:</div>',unsafe_allow_html=True)
    for col,(team,color) in zip(cols2[1:],TEAM_COLORS.items()):
        av=TEAM_AVATARS.get(team,"")
        col.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:13px;color:#4a5568">'
            f'<div style="width:14px;height:14px;border-radius:50%;border:3px solid {color};background:white"></div>{av} {team.split()[0]}</div>',
            unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="padding:8px 0 24px 0">'
            '<div style="font-size:22px;font-weight:800;color:#1a202c">⚙️ Connection</div>'
            '<div style="font-size:13px;color:#718096;margin-top:4px">Azure DevOps · HRM Project</div>'
            '</div>',
            unsafe_allow_html=True
        )
        org  = st.text_input("Organisation URL",  value=st.session_state.get("org_url","https://dev.azure.com/YOUR_ORG"))
        proj = st.text_input("Project Name",      value=st.session_state.get("project","HRM"))
        pat  = st.text_input("Personal Access Token", value=st.session_state.get("pat",""), type="password",
                             help="Needs Work Items (Read) + Project & Team (Read)")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            if st.button("🔄 Load Live", use_container_width=True):
                if org and proj and pat:
                    st.session_state.update({"org_url":org,"project":proj,"pat":pat,
                                             "use_demo":False,"loaded":False})
                    st.cache_data.clear(); st.rerun()
                else: st.error("Please fill all fields")
        with c2:
            if st.button("🧪 Demo", use_container_width=True):
                st.session_state.update({"use_demo":True,"loaded":False}); st.rerun()

        if st.session_state.get("loaded"):
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            if st.button("🔃 Refresh Data", use_container_width=True):
                st.cache_data.clear(); st.session_state["loaded"]=False; st.rerun()

        st.markdown("---")
        st.markdown(
            '<div style="font-size:13px;color:#718096;line-height:2">'
            '<b style="color:#4a5568">PAT Permissions needed:</b><br>'
            '· Work Items → Read<br>'
            '· Project & Team → Read<br><br>'
            '<b style="color:#4a5568">Sprint lookup:</b><br>'
            '· Current sprint first<br>'
            '· Falls back to last sprint<br><br>'
            '<b style="color:#4a5568">Auto-refreshes every 5 min</b>'
            '</div>',
            unsafe_allow_html=True
        )

# ──────────────────────────────────────────────────────────────────
# VIEW 1: ALERT CENTER
# ──────────────────────────────────────────────────────────────────
def render_alert_center(all_data):
    all_items  =[i for t in all_data for i in t.get("items",[])]
    spill_high =[i for i in all_items if i.get("spill_risk")=="high"]
    spill_watch=[i for i in all_items if i.get("spill_risk")=="watch"]
    overs      =[i for i in all_items if i.get("is_overburn")]
    blocked_all=[i for i in all_items if i.get("is_blocked")]
    both       =[i for i in all_items if i.get("spill_risk") in ["high","watch"] and i.get("is_overburn")]
    total_i    =sum(t.get("total",0) for t in all_data)
    done_i     =sum(t.get("done_count",0) for t in all_data)
    comp_pct   =round(done_i/total_i*100) if total_i else 0
    total_ov   =sum(i.get("overrun",0) for i in overs)
    updated_at =datetime.now().strftime("%d %b %Y %H:%M")

    # Per-team date analysis
    active=[t for t in all_data if t.get("sprint_end")]
    ends=[t["sprint_end"] for t in active]
    names=list(dict.fromkeys(t.get("sprint_name","") for t in active))
    earliest=min(ends) if ends else None; latest=max(ends) if ends else None
    all_same=(earliest==latest) if ends else True
    min_dl=min((t.get("days_left",0) for t in active),default=0)
    max_dl=max((t.get("days_left",0) for t in active),default=0)
    if all_same and earliest:
        date_str=f"Sprint ends <b style='color:#1a202c'>{earliest.strftime('%b %d, %Y')}</b>"
        dl_c="#c53030" if min_dl<=2 else "#c05621" if min_dl<=4 else "#4a5568"
        days_str=f"<b style='color:{dl_c}'>{min_dl} working days left</b>"
    else:
        date_str=f"Sprints end <b style='color:#1a202c'>{earliest.strftime('%b %d') if earliest else '—'} – {latest.strftime('%b %d, %Y') if latest else '—'}</b>"
        days_str=f"<b style='color:#c05621'>{min_dl}–{max_dl} days left (varies by team)</b>"
    sprint_label=" · ".join(names[:3]) if names else "—"
    overall="healthy"
    for t in all_data:
        h=t.get("health","no_data")
        if h=="critical": overall="critical"; break
        if h=="atrisk" and overall!="critical": overall="atrisk"
        if h=="watch" and overall not in ["critical","atrisk"]: overall="watch"
    ocfg=HEALTH_CFG[overall]
    past_teams=[t["team"] for t in all_data if t.get("timeframe")=="past"]
    past_note=(f' &nbsp;·&nbsp; <span style="color:#744210;font-size:13px">📅 {", ".join(past_teams)} showing last sprint</span>'
               if past_teams else "")

    # ── BANNER ──
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:6px solid {ocfg["color"]};'
        f'border-radius:12px;padding:22px 30px;margin-bottom:22px;box-shadow:0 2px 10px rgba(0,0,0,0.07)">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div>'
        f'<div style="font-size:12px;color:#718096;letter-spacing:2px;font-weight:700;margin-bottom:4px">'
        f'🚨 SPRINT ALERT CENTER &nbsp;·&nbsp; {sprint_label}</div>'
        f'<div style="font-size:28px;font-weight:900;color:#1a202c;letter-spacing:-0.5px">Sprint Execution Monitor</div>'
        f'<div style="font-size:14px;color:#718096;margin-top:5px">'
        f'5 Teams &nbsp;·&nbsp; HRM Project &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp; {days_str}{past_note}</div>'
        f'</div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:11px;color:#a0aec0;font-weight:600;margin-bottom:8px">OVERALL PI STATUS</div>'
        f'<div style="background:{ocfg["bg"]};border:2px solid {ocfg["border"]};border-radius:10px;padding:10px 22px">'
        f'<span style="font-size:20px;font-weight:900;color:{ocfg["color"]}">{ocfg["icon"]} {ocfg["label"]}</span></div>'
        f'<div style="font-size:13px;color:#a0aec0;margin-top:6px">{comp_pct}% complete &nbsp;·&nbsp; {done_i}/{total_i} items</div>'
        f'<div style="font-size:12px;color:#cbd5e0;margin-top:2px">Updated: {updated_at}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )

    # Connect button (top-right in banner area)
    cb_col1, cb_col2 = st.columns([8,1])
    with cb_col2:
        if st.button("⚙️ Connect", key="connect_btn"):
            st.session_state["show_connect"] = not st.session_state.get("show_connect", False)
            st.rerun()

    # Inline connection panel
    if st.session_state.get("show_connect", False):
        with st.container():
            st.markdown(
                '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;'
                'padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">',
                unsafe_allow_html=True
            )
            cc1,cc2,cc3,cc4,cc5=st.columns([3,2,3,1,1])
            with cc1: org=st.text_input("Org URL",value=st.session_state.get("org_url","https://dev.azure.com/YOUR_ORG"),label_visibility="visible")
            with cc2: proj=st.text_input("Project",value=st.session_state.get("project","HRM"),label_visibility="visible")
            with cc3: pat=st.text_input("PAT",value=st.session_state.get("pat",""),type="password",label_visibility="visible")
            with cc4:
                st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                if st.button("🔄 Load",use_container_width=True):
                    if org and proj and pat:
                        st.session_state.update({"org_url":org,"project":proj,"pat":pat,"use_demo":False,"loaded":False,"show_connect":False})
                        st.cache_data.clear(); st.rerun()
            with cc5:
                st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                if st.button("🧪 Demo",use_container_width=True):
                    st.session_state.update({"use_demo":True,"loaded":False,"show_connect":False}); st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)

    # ── 3 ALERT BOXES ──
    sc="#c53030" if spill_high else "#b7791f" if spill_watch else "#276749"
    oc="#c53030" if len(overs)>=5 else "#c05621" if overs else "#276749"
    bkc="#6b21a8" if blocked_all else "#276749"
    env_c=sum(1 for i in blocked_all if any(t=="Env-Unstable"    for t,_ in i.get("blocked_tags",[])))
    pr_c =sum(1 for i in blocked_all if any(t=="PR-Approval"     for t,_ in i.get("blocked_tags",[])))
    td_c =sum(1 for i in blocked_all if any(t=="Test-Data-Issue" for t,_ in i.get("blocked_tags",[])))

    a1,a2,a3=st.columns(3)
    for col,color,icon,label,count,right_html,footer in [
        (a1,sc,"⚠️","POTENTIAL SPILLOVER",len(spill_high)+len(spill_watch),
         f'<div style="text-align:right">'
         f'<div style="margin-bottom:8px"><span style="font-size:28px;font-weight:900;color:#c53030">{len(spill_high)}</span>'
         f' <span style="font-size:14px;color:#c53030;font-weight:700">HIGH</span></div>'
         f'<div><span style="font-size:28px;font-weight:900;color:#b7791f">{len(spill_watch)}</span>'
         f' <span style="font-size:14px;color:#b7791f;font-weight:700">WATCH</span></div></div>',
         "🔴 Immediate action required" if spill_high else "🟡 Monitor closely" if spill_watch else "✅ Sprint on track"),
        (a2,oc,"🔥","OVERBURN ALERT",len(overs),
         f'<div style="text-align:right">'
         f'<div style="font-size:12px;color:#a0aec0;font-weight:600;margin-bottom:4px">TOTAL OVERRUN</div>'
         f'<div style="font-size:32px;font-weight:900;color:{oc}">+{total_ov:.0f}h</div>'
         f'<div style="font-size:12px;color:#a0aec0">above estimates</div></div>',
         "🔴 Re-plan needed" if total_ov>=20 else "🟠 Overrun detected" if overs else "✅ All within estimate"),
        (a3,bkc,"🚧","EXTERNALLY BLOCKED",len(blocked_all),
         f'<div style="text-align:right;font-size:14px">'
         f'<div style="margin-bottom:5px"><span style="color:#6b21a8;font-weight:700">🌩️ {env_c}</span> <span style="color:#718096">Env Issues</span></div>'
         f'<div style="margin-bottom:5px"><span style="color:#1e40af;font-weight:700">🔀 {pr_c}</span> <span style="color:#718096">PR Pending</span></div>'
         f'<div><span style="color:#9a3412;font-weight:700">🗄️ {td_c}</span> <span style="color:#718096">Test Data</span></div></div>',
         "🚨 Escalate to resolve" if blocked_all else "✅ No external blockers"),
    ]:
        col.markdown(
            f'<div style="background:#ffffff;border:1px solid {color}25;border-top:5px solid {color};'
            f'border-radius:12px;padding:22px 26px;margin-bottom:18px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
            f'<div><div style="font-size:12px;color:#a0aec0;letter-spacing:1px;font-weight:700;margin-bottom:8px">{icon} {label}</div>'
            f'<div style="font-size:56px;font-weight:900;color:{color};line-height:1">{count}</div>'
            f'</div>{right_html}</div>'
            f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid #f7fafc;font-size:13px;color:#718096">{footer}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── TEAM CARDS ──
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:#a0aec0;letter-spacing:1.5px;'
        'text-transform:uppercase;margin:4px 0 14px 0">Team Sprint Status</div>',
        unsafe_allow_html=True
    )
    order={"critical":0,"atrisk":1,"watch":2,"healthy":3,"no_data":4}
    sorted_d=sorted(all_data,key=lambda x:order.get(x.get("health","no_data"),4))
    tcols=st.columns(5)
    for col,td in zip(tcols,sorted_d):
        team=td.get("team",""); h=td.get("health","no_data"); cfg=HEALTH_CFG[h]
        av=TEAM_AVATARS.get(team,"🔷")
        hc=td.get("high_count",0); wc=td.get("watch_count",0)
        oc2=td.get("over_count",0); bk=td.get("blocked_count",0); cp=td.get("comp_pct",0)
        dl=td.get("days_left",0); se=td.get("sprint_end"); sn=td.get("sprint_name","—"); tf=td.get("timeframe","current")
        end_l=se.strftime("%b %d") if se else "—"
        dl_c="#c53030" if dl<=2 else "#c05621" if dl<=4 else "#718096"
        past_b=('<div style="background:#fefcbf;color:#744210;border-radius:4px;padding:2px 8px;'
                'font-size:11px;font-weight:700;margin-bottom:6px;display:inline-block">📅 LAST SPRINT</div>'
                if tf=="past" else "")
        with col:
            st.markdown(
                f'<div style="background:#ffffff;border:1.5px solid {cfg["border"]};border-top:5px solid {cfg["color"]};'
                f'border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06)">'
                f'{past_b}'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
                f'<span style="font-size:22px">{av}</span>'
                f'<div><div style="font-size:14px;font-weight:700;color:#1a202c;line-height:1.3">{team}</div>'
                f'<div style="font-size:12px;color:{cfg["color"]};font-weight:700;margin-top:1px">{cfg["icon"]} {cfg["label"]}</div></div></div>'
                f'<div style="font-size:12px;color:#a0aec0;margin-bottom:10px">'
                f'{sn} &nbsp;·&nbsp; ends {end_l} &nbsp;·&nbsp; <span style="color:{dl_c};font-weight:700">{dl}d left</span></div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:4px;margin-bottom:12px;text-align:center">'
                f'<div style="background:#fff5f5;border-radius:6px;padding:6px 2px"><div style="font-size:16px;font-weight:800;color:#c53030">{hc}</div><div style="font-size:10px;color:#a0aec0;font-weight:600">SPILL</div></div>'
                f'<div style="background:#fffff0;border-radius:6px;padding:6px 2px"><div style="font-size:16px;font-weight:800;color:#b7791f">{wc}</div><div style="font-size:10px;color:#a0aec0;font-weight:600">WATCH</div></div>'
                f'<div style="background:#fffaf0;border-radius:6px;padding:6px 2px"><div style="font-size:16px;font-weight:800;color:#c05621">{oc2}</div><div style="font-size:10px;color:#a0aec0;font-weight:600">OVER</div></div>'
                f'<div style="background:#f5f3ff;border-radius:6px;padding:6px 2px"><div style="font-size:16px;font-weight:800;color:#6b21a8">{bk}</div><div style="font-size:10px;color:#a0aec0;font-weight:600">BLOCK</div></div>'
                f'</div>'
                f'<div style="font-size:11px;color:#a0aec0;font-weight:600;margin-bottom:4px">{cp}% COMPLETE</div>'
                f'<div style="background:#f7fafc;border-radius:4px;height:6px;overflow:hidden">'
                f'<div style="width:{cp}%;height:100%;background:{cfg["color"]};border-radius:4px"></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"View {team.split()[0]} Detail →", key=f"drill_{team}", use_container_width=True):
                st.session_state.update({"view":"team_detail","selected_team":team}); st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── NINE-BOX ──
    with st.expander("🔲 Member Performance Nine-Box Grid — All Teams", expanded=True):
        render_nine_box(all_data)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── ITEMS OUT OF TRACK ──
    col_title, col_dl = st.columns([4,1])
    with col_title:
        st.markdown(
            '<div style="font-size:13px;font-weight:700;color:#a0aec0;letter-spacing:1.5px;'
            'text-transform:uppercase;margin-bottom:12px">🚨 Items Going Out of Track</div>',
            unsafe_allow_html=True
        )
    with col_dl:
        excel_buf=build_excel(all_data)
        st.download_button("📥 Download All — Excel",data=excel_buf,
                           file_name=f"sprint_all_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_all",use_container_width=True)

    t1,t2,t3,t4=st.tabs([
        f"⚠️ Spillover  ({len(spill_high)+len(spill_watch)})",
        f"🔥 Overburn  ({len(overs)})",
        f"🚧 Blocked  ({len(blocked_all)})",
        f"💀 Both Issues  ({len(both)})",
    ])
    with t1:
        items_s=sorted(spill_high+spill_watch,key=lambda x:0 if x.get("spill_risk")=="high" else 1)
        if not items_s: st.success("✅ No spillover risk items across all teams")
        else:
            for i in items_s: item_card(i,all_data,"spill")
    with t2:
        items_o=sorted(overs,key=lambda x:x.get("overrun",0),reverse=True)
        if not items_o: st.success("✅ No overburn items across all teams")
        else:
            for i in items_o: item_card(i,all_data,"overburn")
    with t3:
        if not blocked_all: st.success("✅ No externally blocked items")
        else:
            grouped=defaultdict(list)
            for item in blocked_all:
                for tag,cfg2 in item.get("blocked_tags",[]): grouped[tag].append((item,cfg2))
            for tag,entries in grouped.items():
                tc=BLOCKED_TAGS.get(tag,BLOCKED_TAGS["Blocked"])
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:12px;margin:16px 0 10px 0;'
                    f'padding:12px 18px;background:{tc["bg"]};border-radius:10px;border:1px solid {tc["border"]}">'
                    f'<span style="font-size:22px">{tc["icon"]}</span>'
                    f'<div><div style="font-size:15px;font-weight:700;color:{tc["color"]}">{tc["label"]}'
                    f' <span style="background:{tc["bg"]};color:{tc["color"]};border:1px solid {tc["border"]};'
                    f'border-radius:6px;padding:2px 10px;font-size:12px;margin-left:6px">{len(entries)} items</span></div>'
                    f'<div style="font-size:13px;color:#4a5568;margin-top:2px">{tc["desc"]}</div></div>'
                    f'<div style="margin-left:auto;text-align:right">'
                    f'<div style="font-size:13px;color:#718096">Escalate to: <b style="color:#1a202c">{tc["owner"]}</b></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
                for item,_ in entries: item_card(item,all_data,"blocked")
    with t4:
        if not both: st.success("✅ No items with both spillover and overburn")
        else:
            for i in sorted(both,key=lambda x:x.get("overrun",0),reverse=True):
                item_card(i,all_data,"spill")

# ──────────────────────────────────────────────────────────────────
# VIEW 2: TEAM DETAIL
# ──────────────────────────────────────────────────────────────────
def render_team_detail(tdata, all_data):
    team=tdata.get("team",""); health=tdata.get("health","no_data"); cfg=HEALTH_CFG[health]
    items=tdata.get("items",[]); av=TEAM_AVATARS.get(team,"🔷")
    dl=tdata.get("days_left",0); ss=tdata.get("sprint_start"); se=tdata.get("sprint_end")
    sn=tdata.get("sprint_name","—"); tf=tdata.get("timeframe","current")
    dl_c="#c53030" if dl<=2 else "#c05621" if dl<=4 else "#4a5568"
    date_rng=f"{ss.strftime('%b %d') if ss else '—'} – {se.strftime('%b %d, %Y') if se else '—'}"

    cb,ch=st.columns([1,10])
    with cb:
        if st.button("← Back",key="back_btn"): st.session_state["view"]="alert_center"; st.rerun()
    with ch:
        past_b=(' <span style="background:#fefcbf;color:#744210;border:1px solid #f6e05e;border-radius:6px;'
                'padding:3px 10px;font-size:12px;font-weight:700">📅 LAST SPRINT</span>' if tf=="past" else "")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;padding:4px 0">'
            f'<span style="font-size:28px">{av}</span>'
            f'<div>'
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'<span style="font-size:22px;font-weight:900;color:#1a202c">{team}</span>'
            f'{hbadge(health)}{past_b}'
            f'</div>'
            f'<div style="font-size:14px;color:#718096;margin-top:3px">'
            f'{sn} &nbsp;·&nbsp; {date_rng} &nbsp;·&nbsp; '
            f'<b style="color:{dl_c}">{dl} working days left</b>'
            f'</div></div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    spill_h=[i for i in items if i.get("spill_risk")=="high"]
    spill_w=[i for i in items if i.get("spill_risk")=="watch"]
    overs  =[i for i in items if i.get("is_overburn")]
    blocked=[i for i in items if i.get("is_blocked")]
    done_it=[i for i in items if i["state"] in COMPLETED]
    unest  =[i for i in items if i.get("is_unestimated")]
    datei  =[i for i in items if i.get("has_date_issue")]
    total_est=sum(i.get("est",0) or 0 for i in items)
    total_done=sum(i.get("done",0) or 0 for i in items)
    total_rem=sum(i.get("rem",0) or 0 for i in items)

    k1,k2,k3,k4,k5,k6=st.columns(6)
    def env_c(it): return sum(1 for i in it if any(t=="Env-Unstable" for t,_ in i.get("blocked_tags",[])))
    def pr_c(it):  return sum(1 for i in it if any(t=="PR-Approval" for t,_ in i.get("blocked_tags",[])))
    def td_c(it):  return sum(1 for i in it if any(t=="Test-Data-Issue" for t,_ in i.get("blocked_tags",[])))

    for col,(label,val,sub,color,bg) in zip([k1,k2,k3,k4,k5,k6],[
        ("Total Items",    len(items),             f"{len(done_it)} done",           "#2563eb","#eff6ff"),
        ("🔴 High Spill",  len(spill_h),           "likely to spill",                "#c53030","#fff5f5"),
        ("🟡 Watch",       len(spill_w),           "needs attention",                "#b7791f","#fffff0"),
        ("🔥 Overburn",    len(overs),             "over estimate",                  "#c05621","#fffaf0"),
        ("🚧 Blocked",     len(blocked),           f"🌩️{env_c(blocked)} 🔀{pr_c(blocked)} 🗄️{td_c(blocked)}","#6b21a8","#f5f3ff"),
        ("⚠️ Flags",       len(unest)+len(datei),  f"{len(unest)} unest · {len(datei)} date","#9d174d","#fdf2f8"),
    ]):
        col.markdown(
            f'<div style="background:{bg};border:1px solid {color}25;border-top:4px solid {color};'
            f'border-radius:10px;padding:14px;text-align:center">'
            f'<div style="font-size:11px;color:#718096;letter-spacing:1px;font-weight:700;margin-bottom:5px">{label}</div>'
            f'<div style="font-size:30px;font-weight:900;color:{color};margin:3px 0">{val}</div>'
            f'<div style="font-size:12px;color:#a0aec0">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Hours bar
    col_h, col_dl2 = st.columns([4,1])
    with col_h:
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:14px 22px;'
            f'margin-bottom:16px;display:flex;gap:36px;align-items:center;box-shadow:0 1px 4px rgba(0,0,0,0.05)">'
            f'<div><span style="font-size:12px;color:#a0aec0;font-weight:600">ESTIMATED &nbsp;</span>'
            f'<span style="font-size:16px;font-weight:800;color:#1a202c">{total_est:.0f}h</span></div>'
            f'<div><span style="font-size:12px;color:#a0aec0;font-weight:600">LOGGED &nbsp;</span>'
            f'<span style="font-size:16px;font-weight:800;color:#276749">{total_done:.0f}h</span></div>'
            f'<div><span style="font-size:12px;color:#a0aec0;font-weight:600">REMAINING &nbsp;</span>'
            f'<span style="font-size:16px;font-weight:800;color:#b7791f">{total_rem:.0f}h</span></div>'
            f'<div><span style="font-size:12px;color:#a0aec0;font-weight:600">COMPLETION &nbsp;</span>'
            f'<span style="font-size:16px;font-weight:800;color:#2563eb">{tdata.get("comp_pct",0)}%</span></div>'
            f'<div style="margin-left:auto;font-size:12px;color:#a0aec0">'
            f'Updated: {datetime.now().strftime("%d %b %Y %H:%M")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col_dl2:
        excel_buf=build_excel([tdata])
        st.download_button(f"📥 {team.split()[0]} Excel",data=excel_buf,
                           file_name=f"sprint_{team.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_team",use_container_width=True)

    tab1,tab2,tab3,tab4,tab5=st.tabs([
        f"⚠️ Spillover ({len(spill_h)+len(spill_w)})",
        f"🔥 Overburn ({len(overs)})",
        f"🚧 Blocked ({len(blocked)})",
        f"👥 Member Load",
        f"📋 All Items ({len(items)})",
    ])
    with tab1:
        ss2=sorted(spill_h+spill_w,key=lambda x:0 if x.get("spill_risk")=="high" else 1)
        if not ss2: st.success("✅ No spillover risk")
        else:
            for i in ss2: item_card(i,all_data,"spill")
    with tab2:
        so=sorted(overs,key=lambda x:x.get("overrun",0),reverse=True)
        if not so: st.success("✅ No overburn items")
        else:
            for i in so: item_card(i,all_data,"overburn")
    with tab3:
        if not blocked: st.success("✅ No externally blocked items")
        else:
            grouped=defaultdict(list)
            for item in blocked:
                for tag,cfg2 in item.get("blocked_tags",[]): grouped[tag].append((item,cfg2))
            for tag,entries in grouped.items():
                tc=BLOCKED_TAGS.get(tag,BLOCKED_TAGS["Blocked"])
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:12px;margin:14px 0 10px 0;'
                    f'padding:12px 18px;background:{tc["bg"]};border-radius:10px;border:1px solid {tc["border"]}">'
                    f'<span style="font-size:20px">{tc["icon"]}</span>'
                    f'<span style="font-size:15px;font-weight:700;color:{tc["color"]}">{tc["label"]}</span>'
                    f'<span style="font-size:13px;color:#4a5568;margin-left:6px">→ <b>{tc["owner"]}</b> · {tc["desc"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                for item,_ in entries: item_card(item,all_data,"blocked")
    with tab4:
        render_members(items)
    with tab5:
        render_all_items(items)

def render_members(items):
    mems=defaultdict(lambda:{"items":[],"done":0,"spill":0,"over":0,"block":0,"logged":0,"est":0})
    for item in items:
        a=item.get("assignee","Unassigned"); mems[a]["items"].append(item)
        if item["state"] in COMPLETED:                         mems[a]["done"] +=1
        if item.get("spill_risk") in ["high","watch"]:         mems[a]["spill"]+=1
        if item.get("is_overburn"):                            mems[a]["over"] +=1
        if item.get("is_blocked"):                             mems[a]["block"]+=1
        mems[a]["logged"]+=item.get("done",0) or 0
        mems[a]["est"]   +=item.get("est",0)  or 0
    sorted_m=sorted(mems.items(),key=lambda x:x[1]["spill"]*3+x[1]["over"]*2+x[1]["block"],reverse=True)
    cols=st.columns(min(len(sorted_m),4))
    for idx,(name,data) in enumerate(sorted_m):
        col=cols[idx%4]; total=len(data["items"])
        pct=int(data["done"]/total*100) if total else 0
        bar_c="#276749" if pct>=80 else "#b7791f" if pct>=50 else "#c53030"
        init_s=inits(name)
        has_spill=data["spill"]>0; has_block=data["block"]>0
        border_c="#c53030" if has_spill else "#6b21a8" if has_block else "#e2e8f0"
        av_bg="#fff5f5" if has_spill else "#f5f3ff" if has_block else "#f7fafc"
        av_c="#c53030" if has_spill else "#6b21a8" if has_block else "#718096"
        with col:
            st.markdown(
                f'<div style="background:#ffffff;border:2px solid {border_c};border-radius:12px;'
                f'padding:16px;margin-bottom:14px;box-shadow:0 2px 6px rgba(0,0,0,0.06)">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">'
                f'<div style="width:38px;height:38px;border-radius:50%;background:{av_bg};'
                f'border:2px solid {border_c};display:flex;align-items:center;justify-content:center;'
                f'font-size:13px;font-weight:800;color:{av_c}">{init_s}</div>'
                f'<div><div style="font-size:15px;font-weight:700;color:#1a202c">{name}</div>'
                f'<div style="font-size:12px;color:#a0aec0">{total} items · {data["logged"]:.0f}h logged</div>'
                f'</div></div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-bottom:12px;text-align:center">'
                f'<div style="background:#f0fff4;border-radius:6px;padding:8px 2px">'
                f'<div style="font-size:18px;font-weight:800;color:#276749">{data["done"]}</div>'
                f'<div style="font-size:10px;color:#a0aec0;font-weight:600">DONE</div></div>'
                f'<div style="background:#fff5f5;border-radius:6px;padding:8px 2px">'
                f'<div style="font-size:18px;font-weight:800;color:#c53030">{data["spill"]}</div>'
                f'<div style="font-size:10px;color:#a0aec0;font-weight:600">SPILL</div></div>'
                f'<div style="background:#fffaf0;border-radius:6px;padding:8px 2px">'
                f'<div style="font-size:18px;font-weight:800;color:#c05621">{data["over"]}</div>'
                f'<div style="font-size:10px;color:#a0aec0;font-weight:600">OVER</div></div>'
                f'<div style="background:#f5f3ff;border-radius:6px;padding:8px 2px">'
                f'<div style="font-size:18px;font-weight:800;color:#6b21a8">{data["block"]}</div>'
                f'<div style="font-size:10px;color:#a0aec0;font-weight:600">BLOCK</div></div>'
                f'</div>'
                f'<div style="font-size:12px;color:#a0aec0;font-weight:600;margin-bottom:4px">'
                f'{pct}% COMPLETE · {data["est"]:.0f}h estimated</div>'
                f'<div style="background:#f7fafc;border-radius:4px;height:6px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{bar_c};border-radius:4px"></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )

def render_all_items(items):
    rows=[]
    for i in items:
        sr=i.get("spill_risk","none"); ob=i.get("is_overburn",False)
        bk=i.get("is_blocked",False); un=i.get("is_unestimated",False); di=i.get("has_date_issue",False)
        flags=" ".join(filter(None,[
            "🔴 HIGH" if sr=="high" else "","🟡 WATCH" if sr=="watch" else "",
            "🔥 OVER" if ob else "","🚧 BLOCK" if bk else "",
            "📋 UNEST" if un else "","📅 DATE" if di else ""
        ])) or "✅"
        rows.append({"ID":i.get("id"),"Type":i.get("type",""),"Title":(i["title"][:60]+"…") if len(i["title"])>60 else i["title"],
                     "Assignee":i.get("assignee","—").split()[0],"State":i.get("state",""),
                     "Est(h)":i.get("est") or "—","Done(h)":i.get("done") or "—","Rem(h)":i.get("rem") or "—",
                     "Flags":flags,"Tags":i.get("tags","")[:40],
                     "Feature":(i.get("feature_title","")[:40]+"…") if i.get("feature_title") and len(i.get("feature_title",""))>40 else i.get("feature_title","—")})
    if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=460)
    else: st.info("No items to display.")

# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────
def main():
    for k,v in [("view","alert_center"),("selected_team",TEAMS[0]),("use_demo",True),
                ("loaded",False),("all_data",[]),("show_connect",False),
                ("org_url","https://dev.azure.com/YOUR_ORG"),("project","HRM"),("pat","")]:
        if k not in st.session_state: st.session_state[k]=v

    render_sidebar()

    if not st.session_state["loaded"]:
        if st.session_state.get("use_demo"):
            with st.spinner("Loading demo data…"):
                st.session_state["all_data"]=gen_demo(); st.session_state["loaded"]=True
        elif st.session_state.get("pat"):
            prog=st.progress(0,"Connecting to Azure DevOps…"); all_data=[]
            for idx,team in enumerate(TEAMS):
                prog.progress((idx+1)/len(TEAMS),f"Loading {team}…")
                all_data.append(load_team(st.session_state["org_url"],
                                          st.session_state["project"],
                                          st.session_state["pat"],team))
            st.session_state["all_data"]=all_data; st.session_state["loaded"]=True; prog.empty()
        else:
            st.markdown(
                '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;'
                'min-height:70vh;text-align:center">'
                '<div style="font-size:64px;margin-bottom:24px">🚨</div>'
                '<div style="font-size:32px;font-weight:900;color:#1a202c;margin-bottom:10px">Sprint Alert Center</div>'
                '<div style="font-size:16px;color:#718096;max-width:440px;line-height:1.8">'
                'Connect your Azure DevOps via the sidebar,<br>'
                'or click <b style="color:#2563eb">⚙️ Connect</b> button after loading demo data.'
                '</div>'
                '<div style="margin-top:24px">'
                '</div></div>',
                unsafe_allow_html=True
            )
            col1,col2,col3=st.columns([2,1,2])
            with col2:
                if st.button("🧪 Load Demo Data",use_container_width=True):
                    st.session_state.update({"use_demo":True,"loaded":False}); st.rerun()
            return

    all_data=st.session_state["all_data"]
    view=st.session_state["view"]
    if view=="alert_center": render_alert_center(all_data)
    elif view=="team_detail":
        sel=st.session_state.get("selected_team",TEAMS[0])
        tdata=next((t for t in all_data if t["team"]==sel),None)
        if tdata: render_team_detail(tdata,all_data)
        else: st.session_state["view"]="alert_center"; st.rerun()

if __name__=="__main__": main()
