# 🚀 PI Sprint Command Center

Sprint Visibility Dashboard for 5 Scrum Teams — HRM Project

## Teams
- ⚡ Echo Engineers
- 🛡️ Code Commanders
- 🔥 Beta Brigade
- 🌀 Gamma Guardians
- 💥 Hyper Hackers

## Features
- **Command Center** — 5 team cards ranked by sprint health (Critical / At Risk / Watch / Healthy)
- **Team Sprint Detail** — Spillover risk + Overburn analysis per team
- **Feature Risk Drill-Down** — Task → Backlog Item → Feature → PI delivery risk

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Push this folder to a GitHub repository
2. Go to https://share.streamlit.io
3. Connect your GitHub repo
4. Set main file: `app.py`
5. Add your PAT as a Streamlit Secret (optional — can also enter in the sidebar)

## Azure DevOps Setup
- **Org URL**: `https://dev.azure.com/YOUR_ORG`
- **Project**: Your project name
- **PAT Permissions needed**: Work Items (Read), Project & Team (Read)

## Spillover Detection Logic
| Tier | Signal |
|------|--------|
| 🔴 HIGH | On Hold · Not started + rem > hrs left · Target date beyond sprint end |
| 🟡 WATCH | In Progress < 30% complete · No hours logged · Overburn + still running |

## Overburn Detection
- **Done/Resolved**: `Actual > Estimate`
- **In Progress**: `(Done + Remaining) > Estimate`
