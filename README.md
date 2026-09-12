# boiler_efficiency

Program to calculate boiler efficiency, based on the BOILERE1 program.

## Streamlit app (mobile-friendly)

`app.py` is a Streamlit version of the calculator, designed to be easy to use
from a phone: inputs are grouped into collapsible sections, results are shown
as at-a-glance metrics plus tabbed tables, and you can download an Excel or
text report. `boiler_calc.py` contains the calculation engine, ported line
for line from the original `boiler_eff.html` JavaScript so results match
exactly.

### Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the printed URL. On your phone, open the same URL (use the
"Network URL" Streamlit prints, or deploy it — see below — for access from
anywhere).

### Deploy for phone access

The easiest option is [Streamlit Community Cloud](https://streamlit.io/cloud):
push this repo to GitHub, connect it at share.streamlit.io, and point it at
`app.py`. You'll get a public HTTPS URL that works great on mobile browsers
and can be added to your phone's home screen like an app.

### Keeping the app awake

Streamlit Community Cloud puts apps to sleep after a period without any
visitors, and a sleeping app needs a manual "wake up" click before it's
usable. `.github/workflows/keep-alive.yml` pings the deployed app every 30
minutes so it counts as active traffic and never falls asleep.

One-time setup after your first deploy:

1. Go to the repo's **Settings → Secrets and variables → Actions → Variables** tab.
2. Click **New repository variable**.
3. Name: `STREAMLIT_APP_URL`, Value: your app's URL (e.g. `https://your-app-name.streamlit.app`).

The workflow runs automatically from then on. You can also trigger it manually
from the **Actions** tab (**Keep Streamlit App Awake → Run workflow**) to
verify it's working.

## Original HTML version

`boiler_eff.html` is the original single-file browser version, with the
option to export to PDF or Excel directly from the page.
