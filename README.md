# ClaimSaathi

> **AI-powered, customer-side insurance claim copilot.**
> ClaimSaathi doesn't replace the insurer. It makes the customer better prepared to navigate the insurer.

Built for **Paytm AI Hackathon — Track 2: AI-Powered Financial Journeys.**
Team Static: Siddhartha Jaiswal · Suman Kumar Jha

---

## What it does

ClaimSaathi reduces confusion at three moments in the health-insurance reimbursement journey:

| Moment | Feature | What it does |
|---|---|---|
| Before submission | **Claim Readiness** | Checks documents against a deterministic requirements checklist; flags missing/unclear items; explains in plain language |
| After rejection | **Rejection Decoder** | Parses the rejection letter; retrieves matching policy clause via RAG; explains with FACT / AI INTERPRETATION / RECOMMENDATION |
| Responding | **Appeal Builder** | Generates a structured, evidence-grounded reconsideration draft; customer reviews, edits, and explicitly approves before export |

**ClaimSaathi never approves, rejects, or predicts claim outcomes. The insurer remains the sole regulated decision-maker at every step.**

---

## Quick start (local)

### Prerequisites
- Docker Desktop 4.x+
- An **OpenAI API key** (OPENAI_API_KEY)
- Optionally: Google Cloud Document AI credentials for real OCR (demo works without it via MockOCRAdapter)

### 1. Clone and configure
```
git clone <repo>
cd claimsaathi
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY and a strong SECRET_KEY
```

### 2. Start all services
```
docker-compose -f infrastructure/docker-compose.yml up -d
```

### 3. Run migrations
```
docker-compose -f infrastructure/docker-compose.yml exec backend alembic upgrade head
```

### 4. Seed demo data
```
docker-compose -f infrastructure/docker-compose.yml exec backend python /app/scripts/seed_demo_data.py
```

### 5. Open
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- n8n: http://localhost:5678
- MinIO: http://localhost:9001

### Demo login
Email: ramesh.kumar@demo.claimsaathi.in  Password: DemoPass@2026!

> Demo data only. Ramesh Kumar is fictional. No real personal information used anywhere.

---

## Primary demo path (<=5 minutes)

Dashboard -> Create Claim -> Upload Documents -> Claim Readiness -> Rejection Decoder -> Appeal Builder -> Approve -> Export PDF

---

## Regulatory posture

ClaimSaathi is a customer-side tool only. It is not an insurer, not an NBFC-AA, not a Lending Service Provider.
AI outputs always carry: "AI explanation only. Final claim decision remains with the insurer."
