# 🏢 Talent Groups — Business Pulse Agent 2.0

**[Live Demo →](https://pulse-agent-2-0.vercel.app/)**

An AI agent that synthesizes Bullhorn ATS and Microsoft Dynamics 365 Business Central data into a single, concise executive briefing for the CIO — surfacing billing gaps, AR anomalies, recruiter performance drops, and aged job orders across both systems.

## What It Does

Every morning, the CIO clicks one button and receives:

- **Operational snapshot** — active placements, fill rates, submission pipeline
- **Financial snapshot** — revenue attainment, DSO, AR aging buckets
- **Anomaly detection** — billing gaps (placements with no invoice), overdue AR, stalled job orders
- **Recruiter performance** — week-over-week drops flagged automatically
- **Upcoming risks** — placement end dates with no redeployment plan

## Stack

| Layer | Technology |
|---|---|
| AI Engine | Claude API (Anthropic — `claude-haiku-4-5`) |
| UI | Vanilla HTML/CSS/JS (no framework) |
| API | Vercel Python Serverless Functions |
| Data | Bullhorn REST API + BC OData v2.0 (mock for demo) |
| Language | Python 3.11+ |

## Run Locally

```bash
# 1. Clone
git clone https://github.com/your-username/pulse-agent-2.0.git
cd pulse-agent-2.0

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Serve the frontend (any static server)
npx serve public
```

Then open `http://localhost:3000`. Note: the `/api/generate` endpoint requires Vercel's runtime locally — use `vercel dev` for full local testing:

```bash
npm i -g vercel
vercel dev
```

## Deploy to Vercel

1. Push this repo to GitHub (make sure `.env` is in `.gitignore`)
2. Go to [vercel.com](https://vercel.com) → **New Project** → import your repo
3. Under **Environment Variables**, add:
   ```
   ANTHROPIC_API_KEY = sk-ant-...
   ```
4. Click **Deploy** — live in ~2 minutes

## Project Structure

```
pulse-agent-2.0/
├── public/
│   └── index.html              # Single-page UI (HTML/CSS/JS)
├── api/
│   └── generate.py             # Vercel serverless function (POST /api/generate)
├── agent/
│   ├── fetcher.py              # Loads + cross-references both data sources
│   └── synthesizer.py          # Claude API call + tool-use prompt engineering
├── mock_data/
│   ├── bullhorn/               # Placements, job orders, submissions, clients
│   └── business_central/       # Invoices, customers, payments (AR aging)
├── vercel.json                 # Routing config
└── requirements.txt
```

---

Built by **Bhanu Prakash Simhadri** · Demonstrates AI agent development, data synthesis, and API integration across Bullhorn ATS and Microsoft Dynamics 365 Business Central.
