"""
Sprint Alert Center — PI Execution Dashboard
5 Scrum Teams · HRM Project · Azure DevOps
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

# ─────────────────────────────────────────────────────────────────
# CSS — clean, professional, corporate
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: #ffffff !important;
    color: #1a202c !important;
    font-size: 14px !important;
}
.stApp { background: #f7f9fc; }
.block-container { padding: 1.5rem 2.5rem !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e8ecf0 !important;
}
[data-testid="stSidebar"] * { font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebar"] input {
    background: #f7f9fc !important; border: 1px solid #e8ecf0 !important;
    border-radius: 6px !important; font-size: 13px !important; color: #1a202c !important;
}
[data-testid="stSidebar"] label {
    font-size: 11px !important; font-weight: 600 !important;
    color: #8896a5 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important;
}

.stButton > button {
    font-family: 'Inter', sans-serif !important; font-size: 13px !important;
    font-weight: 600 !important; border-radius: 6px !important;
    border: 1px solid #d1d9e0 !important; background: #ffffff !important;
    color: #374151 !important; padding: 7px 16px !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    border-color: #2563eb !important; color: #2563eb !important; background: #eff6ff !important;
}
.stDownloadButton > button {
    font-family: 'Inter', sans-serif !important; font-size: 13px !important;
    font-weight: 600 !important; border-radius: 6px !important;
    background: #eff6ff !important; color: #2563eb !important;
    border: 1px solid #bfdbfe !important;
}
div[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important; font-size: 14px !important;
    font-weight: 500 !important; color: #6b7280 !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    font-weight: 700 !important; color: #1a202c !important;
}
.stDataFrame { border-radius: 8px !important; }
[data-testid="stMetric"] { background: #ffffff; border-radius: 8px; padding: 1rem; border: 1px solid #e8ecf0; }
[data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] { font-size: 13px !important; font-weight: 600 !important; color: #6b7280 !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f7f9fc; }
::-webkit-scrollbar-thumb { background: #d1d9e0; border-radius: 3px; }
hr { border-color: #e8ecf0 !important; margin: 1rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────
TEAMS        = ["Echo Engineers","Code Commanders","Beta Brigade","Gamma Guardians","Hyper Hackers"]
TEAM_AVATARS = {"Echo Engineers":"⚡","Code Commanders":"🛡️","Beta Brigade":"🔥","Gamma Guardians":"🌀","Hyper Hackers":"💥"}
TEAM_COLORS  = {"Echo Engineers":"#2563eb","Code Commanders":"#7c3aed","Beta Brigade":"#ea580c","Gamma Guardians":"#059669","Hyper Hackers":"#db2777"}
COMPLETED    = ["Done","Resolved","Dev Completed"]
INPROGRESS   = ["In Progress","Scheduled"]
VALID_TYPES  = ["Task","Bug"]

STATUS = {
    "critical": {"color":"#dc2626","bg":"#fef2f2","border":"#fecaca","text":"Critical",  "icon":"🔴"},
    "atrisk":   {"color":"#d97706","bg":"#fffbeb","border":"#fde68a","text":"At Risk",   "icon":"🟡"},
    "watch":    {"color":"#ca8a04","bg":"#fefce8","border":"#fef08a","text":"Watch",     "icon":"🟡"},
    "healthy":  {"color":"#16a34a","bg":"#f0fdf4","border":"#bbf7d0","text":"Healthy",   "icon":"🟢"},
    "no_data":  {"color":"#6b7280","bg":"#f9fafb","border":"#e5e7eb","text":"No Data",   "icon":"⚫"},
}
BLOCKED_TAGS = {
    "Env-Unstable":    {"label":"Environment Unstable","icon":"🌩️","color":"#7c3aed","owner":"DevOps Team",   "desc":"Env unstable — cannot test/deploy"},
    "PR-Approval":     {"label":"PR Awaiting Approval","icon":"🔀","color":"#1d4ed8","owner":"Tech Lead",     "desc":"PR waiting for code review"},
    "Test-Data-Issue": {"label":"Test Data Issue",     "icon":"🗄️","color":"#b45309","owner":"BA / QA Lead", "desc":"Missing or incorrect test data"},
    "Blocked":         {"label":"Blocked",             "icon":"🚧","color":"#dc2626","owner":"Scrum Master", "desc":"Blocked — needs escalation"},
}

# ─────────────────────────────────────────────────────────────────
# AZURE DEVOPS CLIENT
# ─────────────────────────────────────────────────────────────────
class DevOpsClient:
    def __init__(self, org, proj, pat):
        self.org=org.rstrip("/"); self.proj=proj
        tok=base64.b64encode(f":{pat}".encode()).decode()
        self.h={"Authorization":f"Basic {tok}","Content-Type":"application/json"}
    def _get(self,url,p=None):
        try: r=requests.get(url,headers=self.h,params=p,timeout=20); r.raise_for_status(); return r.json()
        except: return None
    def _post(self,url,b):
        try: r=requests.post(url,headers=self.h,json=b,timeout=20); r.raise_for_status(); return r.json()
        except: return None
    def get_sprint(self,team):
        base=f"{self.org}/{self.proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations"
        d=self._get(base,{"$timeframe":"current","api-version":"7.0"})
        if d and d.get("value"): sp=d["value"][0]; sp["_tf"]="current"; return sp
        d=self._get(base,{"$timeframe":"past","api-version":"7.0"})
        if d and d.get("value"):
            sp=sorted(d["value"],key=lambda x:x.get("attributes",{}).get("finishDate",""),reverse=True)[0]
            sp["_tf"]="past"; return sp
        return None
    def get_wi_ids(self,team,iid):
        d=self._get(f"{self.org}/{self.proj}/{requests.utils.quote(team)}/_apis/work/teamsettings/iterations/{iid}/workitems",{"api-version":"7.0"})
        if not d: return []
        return list(set(w["target"]["id"] for w in d.get("workItemRelations",[]) if w.get("target") and w["target"].get("id")))
    def get_wi_batch(self,ids):
        if not ids: return []
        fields=["System.Id","System.Title","System.WorkItemType","System.State","System.AssignedTo",
                "System.Parent","Microsoft.VSTS.Scheduling.OriginalEstimate",
                "Microsoft.VSTS.Scheduling.CompletedWork","Microsoft.VSTS.Scheduling.RemainingWork",
                "Microsoft.VSTS.Common.Priority","Microsoft.VSTS.Common.Activity","System.Tags",
                "Microsoft.VSTS.Scheduling.StartDate","Microsoft.VSTS.Scheduling.TargetDate"]
        out=[]
        for i in range(0,len(ids),200):
            d=self._post(f"{self.org}/_apis/wit/workitemsbatch?api-version=7.0",{"ids":ids[i:i+200],"fields":fields})
            if d: out.extend(d.get("value",[]))
        return out

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def whl(end):
    if not end: return 0
    today=date.today()
    if today>end: return 0
    c=0; cur=today
    while cur<=end:
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

def pd_(v):
    if not v: return None
    try: return datetime.strptime(str(v)[:10],"%Y-%m-%d").date()
    except: return None

def inits(n):
    p=str(n).split(); return "".join(x[0] for x in p[:2]).upper() if p else "?"

def detect_blocked(tags):
    if not tags: return []
    tlist=[t.strip() for t in str(tags).split(";")]
    if "Blocked" not in tlist: return []
    matched=[(s,BLOCKED_TAGS[s]) for s in ["Env-Unstable","PR-Approval","Test-Data-Issue"] if s in tlist]
    return matched or [("Blocked",BLOCKED_TAGS["Blocked"])]

def check_dates(is_,it,ss,se):
    v=[]
    if not is_: v.append("Start date not set")
    elif ss and is_<ss: v.append(f"Start {is_.strftime('%b %d')} before sprint start")
    elif se and is_>se: v.append(f"Start {is_.strftime('%b %d')} after sprint end")
    if not it: v.append("Target date not set")
    elif se and it>se: v.append(f"Target {it.strftime('%b %d')} beyond sprint end")
    return v

def classify_spill(item,hl):
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
        if is_ip and total>4 and prog<0.3:   risk="watch"; reasons.append(f"Only {int(prog*100)}% complete")
        if is_ip and done==0 and rem>0:      risk="watch"; reasons.append("In Progress — 0 hours logged")
        if state=="Scheduled":               risk="watch"; reasons.append("Scheduled — not activated")
        if is_ip and hl>0 and rem>(hl*0.8): risk="watch"; reasons.append(f"{rem}h rem, limited time left")
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
    return sum(3 if i.get("spill_risk")=="high" else 1 if i.get("spill_risk")=="watch" else 0 for i in items) + \
           sum(2 for i in items if i.get("is_overburn")) + \
           sum(1 for i in items if i.get("is_blocked"))

def compute_health(items):
    tasks=[i for i in items if i.get("type") in VALID_TYPES] or items
    n=len(tasks); dc=sum(1 for i in tasks if i["state"] in COMPLETED)
    hc=sum(1 for i in tasks if i.get("spill_risk")=="high")
    wc=sum(1 for i in tasks if i.get("spill_risk")=="watch")
    oc=sum(1 for i in tasks if i.get("is_overburn"))
    bc=sum(1 for i in tasks if i.get("is_blocked"))
    unc=sum(1 for i in tasks if i.get("is_unestimated"))
    dic=sum(1 for i in tasks if i.get("has_date_issue"))
    cp=round(dc/n*100) if n else 0; op=round(oc/n*100) if n else 0
    if hc>=3 or op>=30 or bc>=3: h="critical"
    elif hc>=1 or op>=15 or bc>=1: h="atrisk"
    elif wc>=1 or oc>0: h="watch"
    else: h="healthy"
    return {"health":h,"total":n,"done_count":dc,"high_count":hc,"watch_count":wc,
            "over_count":oc,"blocked_count":bc,"unest_count":unc,"date_issue_count":dic,"comp_pct":cp}

# ─────────────────────────────────────────────────────────────────
# DATA LOADER
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_team(org,proj,pat,team):
    cl=DevOpsClient(org,proj,pat)
    sp=cl.get_sprint(team)
    if not sp:
        return {"team":team,"error":"No sprint found","items":[],"health":"no_data",
                "total":0,"done_count":0,"high_count":0,"watch_count":0,"over_count":0,
                "blocked_count":0,"unest_count":0,"date_issue_count":0,"comp_pct":0}
    attrs=sp.get("attributes",{}); sname=sp.get("name",""); tf=sp.get("_tf","current")
    ss=pd_(attrs.get("startDate")); se=pd_(attrs.get("finishDate"))
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
        is_=pd_(f.get("Microsoft.VSTS.Scheduling.StartDate"))
        it=pd_(f.get("Microsoft.VSTS.Scheduling.TargetDate"))
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
        item.update({"spill_risk":sr,"spill_reasons":rr,"is_overburn":iso,"overrun":ov,"projected":pj,
                     "blocked_tags":bt,"is_blocked":len(bt)>0,"date_violations":dv,
                     "has_date_issue":len(dv)>0,
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

# ─────────────────────────────────────────────────────────────────
# DEMO DATA
# ─────────────────────────────────────────────────────────────────
def gen_demo():
    from random import seed,randint,choice,random,uniform
    seed(42); today=date.today()
    cfgs={"Echo Engineers":  {"h":3,"w":4,"o":5,"b":2,"dp":0.42,"ss":date(2026,5,4),"se":date(2026,5,15)},
          "Code Commanders": {"h":1,"w":3,"o":3,"b":1,"dp":0.60,"ss":date(2026,5,4),"se":date(2026,5,15)},
          "Beta Brigade":    {"h":2,"w":2,"o":4,"b":2,"dp":0.48,"ss":date(2026,4,27),"se":date(2026,5,8)},
          "Gamma Guardians": {"h":0,"w":2,"o":2,"b":0,"dp":0.72,"ss":date(2026,5,4),"se":date(2026,5,15)},
          "Hyper Hackers":   {"h":0,"w":0,"o":0,"b":0,"dp":0.90,"ss":date(2026,4,27),"se":date(2026,5,8)}}
    feats=["Employee Info Module v2","Payroll Engine","Leave Management","Performance Portal","Recruitment Flow"]
    bls=["API Layer","Test Coverage","UI Revamp","Data Migration","Integration Testing","Documentation"]
    mems={"Echo Engineers":["Amila F.","Chamod B.","Hansani G.","Sharini N.","Udara W.","Luqman R."],
          "Code Commanders":["Kasun B.","Praveena G.","Nadith L.","Michelle P.","Iran U.","Maksudul R."],
          "Beta Brigade":["Sammani E.","Mihirani G.","Liyathambara G.","Alex K.","Priya M.","Suresh T."],
          "Gamma Guardians":["Nadia R.","Chen W.","Omar B.","Tara L.","Dev S.","Kim H."],
          "Hyper Hackers":["Raj P.","Fatima A.","Tom B.","Sara L.","Mei X.","Janaka K."]}
    btags=["Blocked; Env-Unstable","Blocked; PR-Approval","Blocked; Test-Data-Issue"]
    all_data=[]; iid=130000
    for team,cfg in cfgs.items():
        items=[]; n=randint(20,28); tm=mems[team]
        ss=cfg["ss"]; se=cfg["se"]; hl=whl(se); dl=wdl(se)
        tf="current" if today<=se else "past"
        sp_name=f"26R1_SP{'06' if tf=='current' else '05'}"
        for j in range(n):
            iid+=1; feat=feats[j%5]; bl=bls[j%6]; mem=tm[j%len(tm)]
            is_h=j<cfg["h"]; is_w=cfg["h"]<=j<cfg["h"]+cfg["w"]
            is_o=j<cfg["o"]; is_b=j<cfg["b"]; is_d=random()<cfg["dp"]
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
            it_=se if j%10!=0 and j%13!=0 else (date(2026,5,30) if j%13==0 else None)
            item={"id":iid,"title":f"[{'DEV' if j%3==0 else 'QA' if j%3==1 else 'BA'}] {bl} — {feat[:35]}",
                  "type":choice(["Task","Task","Task","Bug"]),"state":state,"assignee":mem,
                  "est":est,"done":round(dh,1),"rem":round(max(rh,0),1),
                  "priority":randint(1,3),"activity":choice(["Development","Testing","Documentation"]),
                  "tags":tags,"item_start":is_,"item_target":it_,"parent_id":120000+j,
                  "sprint_name":sp_name,"sprint_start":ss,"sprint_end":se,"team":team,"timeframe":tf,
                  "devops_url":f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{iid}",
                  "backlog_title":bl,"backlog_url":f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{120000+j}",
                  "feature_title":feat,"feature_url":f"https://dev.azure.com/YOUR_ORG/HRM/_workitems/edit/{110000+(j%5)}"}
            sr,rr=classify_spill(item,hl); iso,ov,pj=classify_overburn(item)
            bt=detect_blocked(tags); dv=check_dates(is_,it_,ss,se)
            item.update({"spill_risk":sr,"spill_reasons":rr,"is_overburn":iso,"overrun":ov,"projected":pj,
                         "blocked_tags":bt,"is_blocked":len(bt)>0,"date_violations":dv,
                         "has_date_issue":len(dv)>0,
                         "is_unestimated":(est or 0)==0 and state not in COMPLETED})
            items.append(item)
        h=compute_health(items)
        all_data.append({"team":team,"sprint_name":sp_name,"timeframe":tf,"sprint_start":ss,
                         "sprint_end":se,"hrs_left":hl,"days_left":dl,"items":items,"error":None,**h})
    return all_data

# ─────────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ─────────────────────────────────────────────────────────────────
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
            ws.column_dimensions[col[0].column_letter].width=min(ml+4,55)
    buf.seek(0); return buf

# ─────────────────────────────────────────────────────────────────
# ITEMS → DATAFRAME  (for clean table display)
# ─────────────────────────────────────────────────────────────────
def items_to_df(items, sort_col=None, sort_asc=True):
    rows=[]
    for i in items:
        sr=i.get("spill_risk","none"); ob=i.get("is_overburn",False)
        bk=i.get("is_blocked",False); un=i.get("is_unestimated",False); di=i.get("has_date_issue",False)
        flags=", ".join(filter(None,[
            "🔴 High Spill" if sr=="high" else "🟡 Watch" if sr=="watch" else "",
            "🔥 Overburn"  if ob else "",
            "🚧 Blocked"   if bk else "",
            "📋 No Estimate" if un else "",
            "📅 Date Issue"  if di else "",
        ])) or "✅ OK"
        rows.append({
            "ID":         i.get("id"),
            "Title":      (i["title"][:65]+"…") if len(i["title"])>65 else i["title"],
            "Type":       i.get("type",""),
            "Assignee":   i.get("assignee","—"),
            "State":      i.get("state",""),
            "Est (h)":    i.get("est") or 0,
            "Done (h)":   i.get("done") or 0,
            "Rem (h)":    i.get("rem") or 0,
            "Overrun (h)":i.get("overrun") or 0,
            "Spill Risk": sr.upper() if sr!="none" else "—",
            "Flags":      flags,
            "Feature":    (i.get("feature_title","")[:40]+"…") if i.get("feature_title") and len(i.get("feature_title",""))>40 else i.get("feature_title","—"),
            "Tags":       i.get("tags",""),
            "DevOps Link":i.get("devops_url",""),
        })
    df=pd.DataFrame(rows)
    if sort_col and sort_col in df.columns:
        df=df.sort_values(sort_col,ascending=sort_asc)
    return df

# ─────────────────────────────────────────────────────────────────
# NINE-BOX GRID
# ─────────────────────────────────────────────────────────────────
def build_nine_box_fig(all_data):
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
        risk_n=min(rsc*5,100); dot_sz=max(28,min(est_h*1.6,50))
        if sh>0:    dc="#dc2626"
        elif oc>0:  dc="#ea580c"
        elif bc>0:  dc="#7c3aed"
        elif sw>0:  dc="#ca8a04"
        else:       dc="#16a34a"
        in_crit=risk_n>60 and comp<40
        dots.append({"name":name,"team":team,"x":comp,"y":risk_n,"sz":dot_sz,"dc":dc,
                     "label":name.split()[0] if in_crit else inits(name),"crit":in_crit,
                     "comp":comp,"rsc":rsc,"sh":sh,"sw":sw,"oc":oc,"bc":bc,
                     "total":total,"est_h":est_h,"has_b":bc>0})

    fig=go.Figure()

    # Quadrant fills
    quads=[
        (0,66,40,100,"#fef2f2","🔴  CRITICAL",    "#dc2626"),
        (40,66,75,100,"#fff7ed","🔥  OVERLOADED",  "#ea580c"),
        (75,66,100,100,"#fefce8","⚡  STRETCHED",   "#ca8a04"),
        (0,33,40,66, "#fff7ed","⚠️  STRUGGLING",  "#ea580c"),
        (40,33,75,66, "#fefce8","👁  WATCH",        "#ca8a04"),
        (75,33,100,66,"#f0fdf4","📈  ON TRACK",     "#16a34a"),
        (0,0,40,33,  "#fefce8","🐢  SLOW START",   "#ca8a04"),
        (40,0,75,33, "#f0fdf4","✅  DELIVERING",   "#16a34a"),
        (75,0,100,33,"#f0fdf4","⭐  STAR",         "#16a34a"),
    ]
    for x0,y0,x1,y1,bg,lbl,lc in quads:
        fig.add_shape(type="rect",x0=x0,y0=y0,x1=x1,y1=y1,
                      fillcolor=bg,line=dict(color="#e5e7eb",width=1.5))
        fig.add_annotation(x=(x0+x1)/2,y=(y0+y1)/2+14,text=f"<b>{lbl}</b>",
                           font=dict(size=11,color=lc),showarrow=False,
                           xanchor="center",yanchor="middle")

    # Grid lines
    for v in [40,75]:
        fig.add_shape(type="line",x0=v,y0=0,x1=v,y1=100,line=dict(color="#d1d5db",width=1.5,dash="dash"))
    for h in [33,66]:
        fig.add_shape(type="line",x0=0,y0=h,x1=100,y1=h,line=dict(color="#d1d5db",width=1.5,dash="dash"))

    # Axis labels
    for x,lbl in [(20,"LOW DELIVERY"),(57,"MEDIUM DELIVERY"),(87,"HIGH DELIVERY")]:
        fig.add_annotation(x=x,y=-8,text=f"<b>{lbl}</b>",font=dict(size=10,color="#9ca3af"),showarrow=False,xanchor="center")
    for y,lbl in [(16,"LOW RISK"),(50,"MED RISK"),(83,"HIGH RISK")]:
        fig.add_annotation(x=-5,y=y,text=f"<b>{lbl}</b>",font=dict(size=10,color="#9ca3af"),showarrow=False,xanchor="right",yanchor="middle")

    # Purple ring for blocked
    for d in [x for x in dots if x["has_b"]]:
        fig.add_trace(go.Scatter(x=[d["x"]],y=[d["y"]],mode="markers",
                                 marker=dict(size=d["sz"]+14,color="rgba(124,58,237,0.12)",
                                             line=dict(color="#7c3aed",width=2.5)),
                                 showlegend=False,hoverinfo="skip"))

    # Team color ring
    for d in dots:
        tc=TEAM_COLORS.get(d["team"],"#6b7280")
        fig.add_trace(go.Scatter(x=[d["x"]],y=[d["y"]],mode="markers",
                                 marker=dict(size=d["sz"]+8,color="rgba(255,255,255,0.9)",
                                             line=dict(color=tc,width=3)),
                                 showlegend=False,hoverinfo="skip"))

    # Critical glow
    crit=[d for d in dots if d["crit"]]
    if crit:
        fig.add_trace(go.Scatter(x=[d["x"] for d in crit],y=[d["y"] for d in crit],mode="markers",
                                 marker=dict(size=[d["sz"]+24 for d in crit],
                                             color=["rgba(220,38,38,0.1)" for _ in crit],
                                             line=dict(color="#dc2626",width=1.5)),
                                 showlegend=False,hoverinfo="skip"))

    # Main dots
    for d in dots:
        fig.add_trace(go.Scatter(
            x=[d["x"]],y=[d["y"]],mode="markers+text",
            marker=dict(size=d["sz"],color=d["dc"],opacity=0.9,
                        line=dict(color="rgba(255,255,255,0.8)",width=2)),
            text=f"<b>{d['label']}</b>",textposition="middle center",
            textfont=dict(size=9,color="#ffffff"),
            customdata=[[d["name"],d["team"],d["comp"],d["rsc"],d["sh"],d["sw"],d["oc"],d["bc"],d["total"],d["est_h"]]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Team: %{customdata[1]}<br>"
                "Completion: %{customdata[2]}%<br>"
                "Risk Score: %{customdata[3]}<br>"
                "━━━━━━━━━━━━━━<br>"
                "🔴 High Spill: %{customdata[4]}<br>"
                "🟡 Watch: %{customdata[5]}<br>"
                "🔥 Overburn: %{customdata[6]}<br>"
                "🚧 Blocked: %{customdata[7]}<br>"
                "━━━━━━━━━━━━━━<br>"
                "Total Items: %{customdata[8]}<br>"
                "Est Hours: %{customdata[9]:.0f}h"
                "<extra></extra>"
            ),
            showlegend=False,name=d["name"]
        ))

    fig.update_layout(
        height=520,margin=dict(l=70,r=30,t=60,b=70),
        plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
        title_text="<b>Member Performance Nine-Box — Click a dot to view member details</b>",
        title_x=0.0,
        xaxis=dict(range=[-8,108],showgrid=False,zeroline=False,showticklabels=False,title=""),
        yaxis=dict(range=[-12,108],showgrid=False,zeroline=False,showticklabels=False,title=""),
        clickmode="event+select",
    )
    return fig, dots

def render_nine_box(all_data):
    fig, dots = build_nine_box_fig(all_data)
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="nine_box_chart")

    # Legend
    c1,c2=st.columns(2)
    with c1:
        st.markdown(
            '<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;color:#374151">'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#dc2626;margin-right:5px;vertical-align:middle"></span>High Spill</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ea580c;margin-right:5px;vertical-align:middle"></span>Overburn</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ca8a04;margin-right:5px;vertical-align:middle"></span>Watch</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#16a34a;margin-right:5px;vertical-align:middle"></span>Clean</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;border:3px solid #7c3aed;background:white;margin-right:5px;vertical-align:middle"></span>Blocked (ring)</span>'
            '</div>',
            unsafe_allow_html=True
        )
    with c2:
        team_leg="".join(
            f'<span><span style="display:inline-block;width:12px;height:12px;border-radius:50%;border:3px solid {color};background:white;margin-right:5px;vertical-align:middle"></span>'
            f'{TEAM_AVATARS.get(team,"")} {team.split()[0]}</span>'
            for team,color in TEAM_COLORS.items()
        )
        st.markdown(f'<div style="display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#374151">{team_leg}</div>',unsafe_allow_html=True)

    # Handle click — show member detail table
    if event and event.get("selection") and event["selection"].get("points"):
        pts=event["selection"]["points"]
        if pts:
            clicked_name=pts[0].get("customdata",[None])[0]
            if clicked_name:
                # Find member items
                all_items=[i for t in all_data for i in t.get("items",[])]
                member_items=[i for i in all_items if i.get("assignee")==clicked_name]
                if member_items:
                    team_name=member_items[0].get("team","")
                    tc=TEAM_COLORS.get(team_name,"#2563eb")
                    st.markdown(
                        f'<div style="margin-top:16px;padding:14px 20px;background:#f8fafc;'
                        f'border-left:4px solid {tc};border-radius:8px">'
                        f'<span style="font-size:16px;font-weight:700;color:#1a202c">'
                        f'{clicked_name}</span>'
                        f'<span style="font-size:13px;color:#6b7280;margin-left:10px">{team_name}</span>'
                        f'<span style="font-size:13px;color:#6b7280;margin-left:10px">· {len(member_items)} items</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    # Sort by risk — High first, then Watch, then Overburn
                    df=items_to_df(member_items,sort_col="Spill Risk",sort_asc=True)
                    st.dataframe(df,use_container_width=True,hide_index=True,height=300,
                                 column_config={"DevOps Link":st.column_config.LinkColumn("DevOps Link")})

# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown('<div style="font-size:20px;font-weight:800;color:#1a202c;padding:8px 0 20px">⚙️ Connection</div>',unsafe_allow_html=True)
        org =st.text_input("Organisation URL",value=st.session_state.get("org_url","https://dev.azure.com/YOUR_ORG"))
        proj=st.text_input("Project Name",    value=st.session_state.get("project","HRM"))
        pat =st.text_input("Personal Access Token",value=st.session_state.get("pat",""),type="password")
        c1,c2=st.columns(2)
        with c1:
            if st.button("🔄 Load Live",use_container_width=True):
                if org and proj and pat:
                    st.session_state.update({"org_url":org,"project":proj,"pat":pat,"use_demo":False,"loaded":False})
                    st.cache_data.clear(); st.rerun()
                else: st.error("Fill all fields")
        with c2:
            if st.button("🧪 Demo",use_container_width=True):
                st.session_state.update({"use_demo":True,"loaded":False}); st.rerun()
        if st.session_state.get("loaded"):
            if st.button("🔃 Refresh",use_container_width=True):
                st.cache_data.clear(); st.session_state["loaded"]=False; st.rerun()
        st.markdown("---")
        st.markdown('<div style="font-size:13px;color:#6b7280;line-height:2"><b style="color:#374151">PAT needs:</b><br>· Work Items → Read<br>· Project & Team → Read<br><br><b style="color:#374151">Auto-refreshes every 5 min</b></div>',unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# VIEW 1 — ALERT CENTER
# ─────────────────────────────────────────────────────────────────
def render_alert_center(all_data):
    all_items  =[i for t in all_data for i in t.get("items",[])]
    spill_high =[i for i in all_items if i.get("spill_risk")=="high"]
    spill_watch=[i for i in all_items if i.get("spill_risk")=="watch"]
    overs      =[i for i in all_items if i.get("is_overburn")]
    blocked_all=[i for i in all_items if i.get("is_blocked")]
    unest_all  =[i for i in all_items if i.get("is_unestimated")]
    date_all   =[i for i in all_items if i.get("has_date_issue")]
    both       =[i for i in all_items if i.get("spill_risk") in ["high","watch"] and i.get("is_overburn")]
    total_i    =sum(t.get("total",0) for t in all_data)
    done_i     =sum(t.get("done_count",0) for t in all_data)
    comp_pct   =round(done_i/total_i*100) if total_i else 0
    total_ov   =sum(i.get("overrun",0) for i in overs)
    now        =datetime.now().strftime("%d %b %Y  %H:%M")

    # Per-team date range
    active=[t for t in all_data if t.get("sprint_end")]
    ends=[t["sprint_end"] for t in active]
    earliest=min(ends) if ends else None; latest=max(ends) if ends else None
    all_same=(earliest==latest) if ends else True
    min_dl=min((t.get("days_left",0) for t in active),default=0)
    max_dl=max((t.get("days_left",0) for t in active),default=0)
    if all_same and earliest:
        date_str=f"{earliest.strftime('%d %b %Y')}"
        days_str=f"{min_dl} working days left"
    else:
        date_str=f"{earliest.strftime('%d %b') if earliest else '—'} – {latest.strftime('%d %b %Y') if latest else '—'}"
        days_str=f"{min_dl}–{max_dl} days left (varies by team)"

    # Overall health
    overall="healthy"
    for t in all_data:
        h=t.get("health","no_data")
        if h=="critical": overall="critical"; break
        if h=="atrisk" and overall!="critical": overall="atrisk"
        if h=="watch" and overall not in ["critical","atrisk"]: overall="watch"
    os_=STATUS[overall]
    past_teams=[t["team"] for t in all_data if t.get("timeframe")=="past"]

    # ── HEADER ──
    hcol1, hcol2, hcol3, hcol4 = st.columns([5,1,1,1])
    with hcol1:
        st.markdown(
            f'<div style="padding:4px 0 16px 0">'
            f'<div style="font-size:26px;font-weight:800;color:#1a202c">Sprint Execution Monitor</div>'
            f'<div style="font-size:14px;color:#6b7280;margin-top:4px">'
            f'5 Teams &nbsp;·&nbsp; HRM Project &nbsp;·&nbsp; '
            f'<span style="color:#374151;font-weight:500">{date_str}</span> &nbsp;·&nbsp; '
            f'<span style="color:{"#dc2626" if min_dl<=2 else "#d97706" if min_dl<=4 else "#374151"};font-weight:600">{days_str}</span>'
            + (f' &nbsp;·&nbsp; <span style="color:#92400e">📅 {", ".join(past_teams)} showing last sprint</span>' if past_teams else "")
            + f'</div></div>',
            unsafe_allow_html=True
        )
    with hcol2:
        st.markdown(f'<div style="padding-top:12px;text-align:center"><span style="background:{os_["bg"]};color:{os_["color"]};border:1px solid {os_["border"]};border-radius:20px;padding:4px 14px;font-size:13px;font-weight:700">{os_["icon"]} {os_["text"].upper()}</span><div style="font-size:12px;color:#9ca3af;margin-top:4px">{comp_pct}% · {done_i}/{total_i}</div></div>',unsafe_allow_html=True)
    with hcol3:
        if st.button("🔲 Nine-Box",use_container_width=True):
            st.session_state["show_nine_box"]=not st.session_state.get("show_nine_box",False); st.rerun()
    with hcol4:
        if st.button("⚙️ Connect",use_container_width=True):
            st.session_state["show_connect"]=not st.session_state.get("show_connect",False); st.rerun()

    # Inline connect panel
    if st.session_state.get("show_connect",False):
        with st.container():
            st.markdown('<div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;padding:16px 20px;margin-bottom:16px">',unsafe_allow_html=True)
            cc1,cc2,cc3,cc4,cc5=st.columns([3,2,3,1,1])
            with cc1: org=st.text_input("Org URL",value=st.session_state.get("org_url","https://dev.azure.com/YOUR_ORG"),key="c_org")
            with cc2: proj=st.text_input("Project",value=st.session_state.get("project","HRM"),key="c_proj")
            with cc3: pat=st.text_input("PAT",value=st.session_state.get("pat",""),type="password",key="c_pat")
            with cc4:
                st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                if st.button("Load",key="c_load",use_container_width=True):
                    if org and proj and pat:
                        st.session_state.update({"org_url":org,"project":proj,"pat":pat,"use_demo":False,"loaded":False,"show_connect":False})
                        st.cache_data.clear(); st.rerun()
            with cc5:
                st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                if st.button("Demo",key="c_demo",use_container_width=True):
                    st.session_state.update({"use_demo":True,"loaded":False,"show_connect":False}); st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:12px;color:#d1d5db;margin-bottom:16px">Last updated: {now}</div>',unsafe_allow_html=True)
    st.markdown("---")

    # ── METRICS ROW ──
    m1,m2,m3,m4,m5,m6=st.columns(6)
    env_c=sum(1 for i in blocked_all if any(t=="Env-Unstable"    for t,_ in i.get("blocked_tags",[])))
    pr_c =sum(1 for i in blocked_all if any(t=="PR-Approval"     for t,_ in i.get("blocked_tags",[])))
    td_c =sum(1 for i in blocked_all if any(t=="Test-Data-Issue" for t,_ in i.get("blocked_tags",[])))
    with m1: st.metric("⚠️ Potential Spillover", len(spill_high)+len(spill_watch), f"{len(spill_high)} High · {len(spill_watch)} Watch")
    with m2: st.metric("🔥 Overburn Items",      len(overs),                       f"+{total_ov:.0f}h total overrun")
    with m3: st.metric("🚧 Externally Blocked",  len(blocked_all),                 f"🌩️{env_c} 🔀{pr_c} 🗄️{td_c}")
    with m4: st.metric("📋 No Estimate",          len(unest_all),                  "items without effort")
    with m5: st.metric("📅 Date Issues",           len(date_all),                  "missing or out of range")
    with m6: st.metric("✅ Completed",             f"{comp_pct}%",                  f"{done_i} of {total_i} items")

    st.markdown("---")

    # ── NINE BOX (toggle) ──
    if st.session_state.get("show_nine_box",False):
        st.markdown('<div style="font-size:16px;font-weight:700;color:#1a202c;margin-bottom:12px">Member Performance Nine-Box</div>',unsafe_allow_html=True)
        render_nine_box(all_data)
        st.markdown("---")

    # ── TEAM CARDS ──
    st.markdown('<div style="font-size:16px;font-weight:700;color:#1a202c;margin-bottom:14px">Team Sprint Status</div>',unsafe_allow_html=True)
    order={"critical":0,"atrisk":1,"watch":2,"healthy":3,"no_data":4}
    sorted_d=sorted(all_data,key=lambda x:order.get(x.get("health","no_data"),4))
    tcols=st.columns(5)
    for col,td in zip(tcols,sorted_d):
        team=td.get("team",""); h=td.get("health","no_data"); s=STATUS[h]
        av=TEAM_AVATARS.get(team,"🔷"); tc=TEAM_COLORS.get(team,"#2563eb")
        hc=td.get("high_count",0); wc=td.get("watch_count",0)
        oc=td.get("over_count",0); bk=td.get("blocked_count",0)
        uc=td.get("unest_count",0); dc=td.get("date_issue_count",0)
        cp=td.get("comp_pct",0); dl=td.get("days_left",0)
        ss2=td.get("sprint_start"); se2=td.get("sprint_end"); tf=td.get("timeframe","current")
        # Date tag
        date_tag=""
        if ss2 and se2:
            date_tag=(f'<span style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;'
                      f'border-radius:4px;padding:2px 8px;font-size:11px;font-weight:500;margin-left:8px">'
                      f'{ss2.strftime("%b %d")} → {se2.strftime("%b %d")}</span>')
        past_tag=('<span style="background:#fef3c7;color:#92400e;border-radius:4px;padding:2px 6px;font-size:10px;font-weight:700;margin-left:4px">LAST SPRINT</span>' if tf=="past" else "")
        dl_c="#dc2626" if dl<=2 else "#d97706" if dl<=4 else "#6b7280"
        with col:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-top:4px solid {s["color"]};'
                f'border-radius:10px;padding:16px;margin-bottom:4px">'
                # Team name + date tag
                f'<div style="margin-bottom:10px">'
                f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:4px">'
                f'<span style="font-size:18px">{av}</span>'
                f'<span style="font-size:14px;font-weight:700;color:#1a202c">{team}</span>'
                f'{date_tag}{past_tag}</div>'
                f'<div style="display:flex;align-items:center;gap:8px">'
                f'<span style="background:{s["bg"]};color:{s["color"]};border:1px solid {s["border"]};'
                f'border-radius:12px;padding:1px 10px;font-size:11px;font-weight:700">{s["icon"]} {s["text"].upper()}</span>'
                f'<span style="font-size:12px;color:{dl_c};font-weight:600">{dl}d left</span>'
                f'</div></div>'
                # Metrics grid
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:10px">'
                f'<div style="text-align:center;background:#fef2f2;border-radius:6px;padding:6px">'
                f'<div style="font-size:20px;font-weight:800;color:#dc2626">{hc}</div>'
                f'<div style="font-size:10px;color:#6b7280;font-weight:600">HIGH SPILL</div></div>'
                f'<div style="text-align:center;background:#fffbeb;border-radius:6px;padding:6px">'
                f'<div style="font-size:20px;font-weight:800;color:#d97706">{wc}</div>'
                f'<div style="font-size:10px;color:#6b7280;font-weight:600">WATCH</div></div>'
                f'<div style="text-align:center;background:#fff7ed;border-radius:6px;padding:6px">'
                f'<div style="font-size:20px;font-weight:800;color:#ea580c">{oc}</div>'
                f'<div style="font-size:10px;color:#6b7280;font-weight:600">OVERBURN</div></div>'
                f'<div style="text-align:center;background:#f5f3ff;border-radius:6px;padding:6px">'
                f'<div style="font-size:20px;font-weight:800;color:#7c3aed">{bk}</div>'
                f'<div style="font-size:10px;color:#6b7280;font-weight:600">BLOCKED</div></div>'
                f'<div style="text-align:center;background:#ecfeff;border-radius:6px;padding:6px">'
                f'<div style="font-size:20px;font-weight:800;color:#0891b2">{uc}</div>'
                f'<div style="font-size:10px;color:#6b7280;font-weight:600">NO EST</div></div>'
                f'<div style="text-align:center;background:#fdf2f8;border-radius:6px;padding:6px">'
                f'<div style="font-size:20px;font-weight:800;color:#db2777">{dc}</div>'
                f'<div style="font-size:10px;color:#6b7280;font-weight:600">DATE ISSUE</div></div>'
                f'</div>'
                # Progress bar
                f'<div style="font-size:11px;color:#9ca3af;margin-bottom:4px;font-weight:600">{cp}% COMPLETE</div>'
                f'<div style="background:#f3f4f6;border-radius:4px;height:6px;overflow:hidden">'
                f'<div style="width:{cp}%;height:100%;background:{s["color"]};border-radius:4px"></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"View {team.split()[0]} →",key=f"d_{team}",use_container_width=True):
                st.session_state.update({"view":"team_detail","selected_team":team}); st.rerun()

    st.markdown("---")

    # ── ITEMS OUT OF TRACK ──
    col_t, col_dl = st.columns([5,1])
    with col_t:
        st.markdown('<div style="font-size:16px;font-weight:700;color:#1a202c;margin-bottom:2px">Items Going Out of Track</div>',unsafe_allow_html=True)
    with col_dl:
        buf=build_excel(all_data)
        st.download_button("📥 Download Excel",data=buf,
                           file_name=f"sprint_all_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_all",use_container_width=True)

    tabs=st.tabs([
        f"⚠️ Spillover ({len(spill_high)+len(spill_watch)})",
        f"🔥 Overburn ({len(overs)})",
        f"🚧 Blocked ({len(blocked_all)})",
        f"📋 No Estimate ({len(unest_all)})",
        f"📅 Date Issues ({len(date_all)})",
        f"💀 Both Issues ({len(both)})",
    ])

    def show_table(items, sort_col, asc=True, height=400):
        if not items:
            st.success("✅ No items in this category")
            return
        df=items_to_df(items,sort_col,asc)
        st.dataframe(df,use_container_width=True,hide_index=True,height=height,
                     column_config={"DevOps Link":st.column_config.LinkColumn("DevOps Link",display_text="Open ↗")})

    with tabs[0]: show_table(sorted(spill_high+spill_watch,key=lambda x:0 if x.get("spill_risk")=="high" else 1),"Spill Risk")
    with tabs[1]: show_table(sorted(overs,key=lambda x:x.get("overrun",0),reverse=True),"Overrun (h)",asc=False)
    with tabs[2]:
        if not blocked_all: st.success("✅ No externally blocked items")
        else:
            grouped=defaultdict(list)
            for item in blocked_all:
                for tag,cfg2 in item.get("blocked_tags",[]): grouped[tag].append(item)
            for tag,items2 in grouped.items():
                tc2=BLOCKED_TAGS.get(tag,BLOCKED_TAGS["Blocked"])
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;padding:10px 16px;'
                    f'background:#f8fafc;border-left:4px solid {tc2["color"]};border-radius:6px;margin-bottom:8px">'
                    f'<span style="font-size:18px">{tc2["icon"]}</span>'
                    f'<div><b style="color:{tc2["color"]}">{tc2["label"]}</b> '
                    f'<span style="color:#6b7280">· {len(items2)} items · Escalate to: <b>{tc2["owner"]}</b></span></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                show_table(items2,"Rem (h)",asc=False,height=250)
    with tabs[3]: show_table(unest_all,"State",height=400)
    with tabs[4]:
        if not date_all: st.success("✅ No date issues detected")
        else:
            rows2=[]
            for i in date_all:
                rows2.append({"ID":i.get("id"),"Title":(i["title"][:60]+"…") if len(i["title"])>60 else i["title"],
                              "Assignee":i.get("assignee",""),"State":i.get("state",""),"Team":i.get("team",""),
                              "Date Issues":" | ".join(i.get("date_violations",[])),
                              "Item Start":str(i.get("item_start","")) or "NOT SET",
                              "Item Target":str(i.get("item_target","")) or "NOT SET",
                              "Sprint Start":str(i.get("sprint_start","")),
                              "Sprint End":str(i.get("sprint_end","")),
                              "DevOps Link":i.get("devops_url","")})
            df2=pd.DataFrame(rows2)
            st.dataframe(df2,use_container_width=True,hide_index=True,height=400,
                         column_config={"DevOps Link":st.column_config.LinkColumn("DevOps Link",display_text="Open ↗")})
    with tabs[5]: show_table(sorted(both,key=lambda x:x.get("overrun",0),reverse=True),"Overrun (h)",asc=False)

# ─────────────────────────────────────────────────────────────────
# VIEW 2 — TEAM DETAIL
# ─────────────────────────────────────────────────────────────────
def render_team_detail(tdata, all_data):
    team=tdata.get("team",""); health=tdata.get("health","no_data"); s=STATUS[health]
    items=tdata.get("items",[]); av=TEAM_AVATARS.get(team,"🔷")
    dl=tdata.get("days_left",0); ss=tdata.get("sprint_start"); se=tdata.get("sprint_end")
    sn=tdata.get("sprint_name","—"); tf=tdata.get("timeframe","current")
    dl_c="#dc2626" if dl<=2 else "#d97706" if dl<=4 else "#374151"
    date_rng=f"{ss.strftime('%d %b') if ss else '—'} → {se.strftime('%d %b %Y') if se else '—'}"

    # Header
    cb,ch=st.columns([1,10])
    with cb:
        if st.button("← Back"): st.session_state["view"]="alert_center"; st.rerun()
    with ch:
        past_b=(' <span style="background:#fef3c7;color:#92400e;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700">LAST SPRINT</span>' if tf=="past" else "")
        st.markdown(
            f'<div style="padding:4px 0">'
            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
            f'<span style="font-size:26px">{av}</span>'
            f'<span style="font-size:22px;font-weight:800;color:#1a202c">{team}</span>'
            f'<span style="background:{s["bg"]};color:{s["color"]};border:1px solid {s["border"]};border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700">{s["icon"]} {s["text"].upper()}</span>'
            f'{past_b}</div>'
            f'<div style="font-size:14px;color:#6b7280;margin-top:4px">'
            f'{sn} &nbsp;·&nbsp; <span style="background:#f1f5f9;color:#374151;border-radius:4px;padding:2px 8px;font-size:13px;font-weight:500">{date_rng}</span>'
            f' &nbsp;·&nbsp; <span style="color:{dl_c};font-weight:600">{dl} working days left</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)

    # KPI metrics
    spill_h=[i for i in items if i.get("spill_risk")=="high"]
    spill_w=[i for i in items if i.get("spill_risk")=="watch"]
    overs  =[i for i in items if i.get("is_overburn")]
    blocked=[i for i in items if i.get("is_blocked")]
    done_it=[i for i in items if i["state"] in COMPLETED]
    unest  =[i for i in items if i.get("is_unestimated")]
    datei  =[i for i in items if i.get("has_date_issue")]
    total_est =sum(i.get("est",0) or 0 for i in items)
    total_done=sum(i.get("done",0) or 0 for i in items)
    total_rem =sum(i.get("rem",0) or 0 for i in items)

    k1,k2,k3,k4,k5,k6,k7=st.columns(7)
    with k1: st.metric("Total Items",    len(items),       f"{len(done_it)} done")
    with k2: st.metric("🔴 High Spill",  len(spill_h),    "likely to spill")
    with k3: st.metric("🟡 Watch",       len(spill_w),    "needs attention")
    with k4: st.metric("🔥 Overburn",    len(overs),      f"+{sum(i.get('overrun',0) for i in overs):.0f}h")
    with k5: st.metric("🚧 Blocked",     len(blocked),    "external dependency")
    with k6: st.metric("📋 No Estimate", len(unest),      "missing effort")
    with k7: st.metric("📅 Date Issues", len(datei),      "fix before sprint")

    # Hours summary + Excel
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;'
        f'padding:12px 20px;margin:12px 0;display:flex;gap:32px;align-items:center">'
        f'<div><span style="font-size:12px;color:#9ca3af;font-weight:600">ESTIMATED </span>'
        f'<span style="font-size:16px;font-weight:800;color:#1a202c">{total_est:.0f}h</span></div>'
        f'<div><span style="font-size:12px;color:#9ca3af;font-weight:600">LOGGED </span>'
        f'<span style="font-size:16px;font-weight:800;color:#16a34a">{total_done:.0f}h</span></div>'
        f'<div><span style="font-size:12px;color:#9ca3af;font-weight:600">REMAINING </span>'
        f'<span style="font-size:16px;font-weight:800;color:#d97706">{total_rem:.0f}h</span></div>'
        f'<div><span style="font-size:12px;color:#9ca3af;font-weight:600">COMPLETION </span>'
        f'<span style="font-size:16px;font-weight:800;color:#2563eb">{tdata.get("comp_pct",0)}%</span></div>'
        f'<div style="margin-left:auto;font-size:12px;color:#d1d5db">Updated: {datetime.now().strftime("%d %b %Y %H:%M")}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    dl_col1, dl_col2 = st.columns([5,1])
    with dl_col2:
        buf=build_excel([tdata])
        st.download_button(f"📥 {team.split()[0]} Excel",data=buf,
                           file_name=f"sprint_{team.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_t",use_container_width=True)

    # Tabs
    tab1,tab2,tab3,tab4,tab5,tab6=st.tabs([
        f"⚠️ Spillover ({len(spill_h)+len(spill_w)})",
        f"🔥 Overburn ({len(overs)})",
        f"🚧 Blocked ({len(blocked)})",
        f"⚠️ Data Quality ({len(unest)+len(datei)})",
        f"👥 Members",
        f"📋 All Items ({len(items)})",
    ])

    def show_df(its, sc=None, asc=True, h=380):
        if not its: st.success("✅ Nothing to show here"); return
        df=items_to_df(its,sc,asc)
        st.dataframe(df,use_container_width=True,hide_index=True,height=h,
                     column_config={"DevOps Link":st.column_config.LinkColumn("DevOps Link",display_text="Open ↗")})

    with tab1: show_df(sorted(spill_h+spill_w,key=lambda x:0 if x.get("spill_risk")=="high" else 1),"Spill Risk")
    with tab2: show_df(sorted(overs,key=lambda x:x.get("overrun",0),reverse=True),"Overrun (h)",asc=False)
    with tab3:
        if not blocked: st.success("✅ No blocked items")
        else:
            grouped=defaultdict(list)
            for item in blocked:
                for tag,_ in item.get("blocked_tags",[]): grouped[tag].append(item)
            for tag,its in grouped.items():
                tc2=BLOCKED_TAGS.get(tag,BLOCKED_TAGS["Blocked"])
                st.markdown(f'<div style="padding:8px 14px;background:#f8fafc;border-left:4px solid {tc2["color"]};border-radius:6px;margin-bottom:8px"><b style="color:{tc2["color"]}">{tc2["icon"]} {tc2["label"]}</b> <span style="color:#6b7280">· Escalate to: <b>{tc2["owner"]}</b></span></div>',unsafe_allow_html=True)
                show_df(its,"Rem (h)",asc=False,h=220)
    with tab4:
        if not unest and not datei: st.success("✅ No data quality issues")
        else:
            if unest:
                st.markdown('<div style="font-size:14px;font-weight:600;color:#0891b2;margin-bottom:8px">📋 Items Without Original Estimate</div>',unsafe_allow_html=True)
                show_df(unest,"State",h=280)
            if datei:
                st.markdown('<div style="font-size:14px;font-weight:600;color:#db2777;margin:12px 0 8px">📅 Items With Date Issues</div>',unsafe_allow_html=True)
                rows2=[]
                for i in datei:
                    rows2.append({"ID":i.get("id"),"Title":(i["title"][:55]+"…") if len(i["title"])>55 else i["title"],
                                  "Assignee":i.get("assignee",""),"State":i.get("state",""),
                                  "Issue":" | ".join(i.get("date_violations",[])),
                                  "Item Start":str(i.get("item_start","")) or "NOT SET",
                                  "Item Target":str(i.get("item_target","")) or "NOT SET",
                                  "DevOps Link":i.get("devops_url","")})
                df2=pd.DataFrame(rows2)
                st.dataframe(df2,use_container_width=True,hide_index=True,height=280,
                             column_config={"DevOps Link":st.column_config.LinkColumn("DevOps Link",display_text="Open ↗")})
    with tab5: render_members(items)
    with tab6: show_df(items,"Flags",h=460)

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
        bar_c="#16a34a" if pct>=80 else "#d97706" if pct>=50 else "#dc2626"
        has_spill=data["spill"]>0; has_block=data["block"]>0
        border_c="#dc2626" if has_spill else "#7c3aed" if has_block else "#e5e7eb"
        with col:
            st.markdown(
                f'<div style="background:#ffffff;border:2px solid {border_c};border-radius:10px;padding:16px;margin-bottom:12px">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">'
                f'<div style="width:36px;height:36px;border-radius:50%;background:{"#fef2f2" if has_spill else "#f5f3ff" if has_block else "#f1f5f9"};'
                f'border:2px solid {border_c};display:flex;align-items:center;justify-content:center;'
                f'font-size:12px;font-weight:800;color:{border_c}">{inits(name)}</div>'
                f'<div><div style="font-size:14px;font-weight:700;color:#1a202c">{name}</div>'
                f'<div style="font-size:12px;color:#9ca3af">{total} items · {data["logged"]:.0f}h logged</div></div></div>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-bottom:10px;text-align:center">'
                f'<div style="background:#f0fdf4;border-radius:6px;padding:6px"><div style="font-size:18px;font-weight:800;color:#16a34a">{data["done"]}</div><div style="font-size:10px;color:#6b7280;font-weight:600">DONE</div></div>'
                f'<div style="background:#fef2f2;border-radius:6px;padding:6px"><div style="font-size:18px;font-weight:800;color:#dc2626">{data["spill"]}</div><div style="font-size:10px;color:#6b7280;font-weight:600">SPILL</div></div>'
                f'<div style="background:#fff7ed;border-radius:6px;padding:6px"><div style="font-size:18px;font-weight:800;color:#ea580c">{data["over"]}</div><div style="font-size:10px;color:#6b7280;font-weight:600">OVER</div></div>'
                f'<div style="background:#f5f3ff;border-radius:6px;padding:6px"><div style="font-size:18px;font-weight:800;color:#7c3aed">{data["block"]}</div><div style="font-size:10px;color:#6b7280;font-weight:600">BLOCK</div></div>'
                f'</div>'
                f'<div style="font-size:11px;color:#9ca3af;font-weight:600;margin-bottom:4px">{pct}% COMPLETE · {data["est"]:.0f}h est</div>'
                f'<div style="background:#f3f4f6;border-radius:4px;height:5px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{bar_c};border-radius:4px"></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )

# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    for k,v in [("view","alert_center"),("selected_team",TEAMS[0]),("use_demo",True),
                ("loaded",False),("all_data",[]),("show_connect",False),("show_nine_box",False),
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
                all_data.append(load_team(st.session_state["org_url"],st.session_state["project"],st.session_state["pat"],team))
            st.session_state["all_data"]=all_data; st.session_state["loaded"]=True; prog.empty()
        else:
            st.markdown('<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70vh;text-align:center"><div style="font-size:56px;margin-bottom:20px">🚨</div><div style="font-size:28px;font-weight:800;color:#1a202c;margin-bottom:8px">Sprint Alert Center</div><div style="font-size:15px;color:#6b7280;line-height:1.7">Connect your Azure DevOps via the sidebar<br>or load demo data to explore.</div></div>',unsafe_allow_html=True)
            _,cc,_=st.columns([3,2,3])
            with cc:
                if st.button("🧪 Load Demo Data",use_container_width=True):
                    st.session_state.update({"use_demo":True,"loaded":False}); st.rerun()
            return

    all_data=st.session_state["all_data"]
    view=st.session_state["view"]
    if view=="alert_center": render_alert_center(all_data)
    elif view=="team_detail":
        sel=st.session_state.get("selected_team",TEAMS[0])
        td=next((t for t in all_data if t["team"]==sel),None)
        if td: render_team_detail(td,all_data)
        else: st.session_state["view"]="alert_center"; st.rerun()

if __name__=="__main__": main()
