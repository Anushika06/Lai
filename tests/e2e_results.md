# E2E Test Results

## Scope

This E2E package covers the Task 1 flow from `CONTRIBUTING.md`:

- Upload three sample contracts.
- Verify extraction of all seven target clause types: indemnity, limitation of liability, governing law, termination, IP ownership, payment terms, and confidentiality.
- Verify planted risk language is preserved and scored.
- Verify executive summaries are readable.
- Compare the same clause types across all three contracts.
- Ask at least five chat questions per contract.
- Capture screenshots of the UI flow.

## Test Artifacts

| Artifact | Purpose |
| --- | --- |
| `test-contracts/standard_nda.docx` | Low-risk NDA with balanced mutual terms. |
| `test-contracts/risky_saas.docx` | Medium-high-risk SaaS agreement with one-sided payment, indemnity, liability, renewal, and IP terms. |
| `test-contracts/employment_contract.docx` | High-risk employment agreement with uncapped liability, immediate termination, broad IP assignment, waiver language, and restrictive covenant language. |
| `tests/e2e_api_check.py` | Runnable API-level E2E check for upload, analysis, clauses, summary, comparison, and chat. |
| `tests/screenshots/` | Folder for UI screenshots captured during manual verification. |

## Current Run Status

Status: **Ready to execute; not run in this checkout.**

Reason: this workspace does not currently include a backend virtual environment or `.env` file with `GEMINI_API_KEY`. The live pipeline requires PostgreSQL, Docling dependencies, and Gemini access.

## How To Run

From the repository root:

```bash
docker compose up -d
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Add GEMINI_API_KEY to backend/.env
uvicorn app.main:app --reload
```

In a second terminal:

```bash
python tests/e2e_api_check.py --base-url http://localhost:8000
```

For UI screenshots, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`, upload each sample contract, wait for analysis completion, and save screenshots into `tests/screenshots/`.

## Expected Results Matrix

| Contract | Expected clause coverage | Expected risk behavior | Expected summary behavior |
| --- | --- | --- | --- |
| `standard_nda.docx` | All seven target clause types extracted. | Overall low to medium. Risk-reducing terms should include mutual obligations, liability cap, and 30-day notice. | Plain-English summary should describe a balanced mutual NDA. |
| `risky_saas.docx` | All seven target clause types extracted. | Overall medium-high to critical. Scoring should flag unlimited customer liability, no cap on damages, unilateral discretion, auto-renewal, penalty language, perpetual confidentiality, and broad IP assignment. | Summary should call out customer-heavy risk allocation and negotiation points. |
| `employment_contract.docx` | All seven target clause types extracted. | Overall high to critical. Scoring should flag unlimited liability, immediate termination, irrevocable full IP assignment, broad indemnity, waiver language, and non-compete/restrictive covenant language. | Summary should identify employee-side risk and the most aggressive provisions. |

## Chat Questions

Ask each of the following questions for each contract:

1. What are the top three risks in this contract?
2. Who carries the indemnity risk?
3. Does the contract include a liability cap?
4. How can the contract be terminated?
5. Summarize the confidentiality obligation in plain English.

Expected behavior: each answer should be readable, contract-specific, and cite relevant sections when the backend returns citations.

## Clause Comparison Checks

Run comparison across all three uploaded contracts for each target clause type:

- `indemnity`
- `limitation_of_liability`
- `governing_law`
- `termination`
- `ip_ownership`
- `payment_terms`
- `confidentiality`

Expected behavior: each comparison should return one entry per contract. AI comparison fields may vary by model response, but raw comparison entries must include the correct clause text and risk score for each contract.

## Screenshot Checklist

Save screenshots in `tests/screenshots/` using these suggested names:

| Screenshot | What it should show |
| --- | --- |
| `01-upload-standard-nda.png` | Standard NDA selected or uploaded in the UI. |
| `02-standard-nda-analysis.png` | Completed NDA analysis with extracted clauses. |
| `03-risky-saas-analysis.png` | Completed SaaS analysis showing elevated risk. |
| `04-employment-analysis.png` | Completed employment contract analysis showing high risk. |
| `05-compare-limitation-liability.png` | Comparison view for limitation of liability across all three contracts. |
| `06-chat-employment.png` | Chat answer for one employment contract risk question. |

## Manual Result Log

Fill this section after running the checks:

| Check | Result | Notes |
| --- | --- | --- |
| Backend health at `/api/health` | Pending |  |
| Upload all three contracts | Pending |  |
| Analysis completes for all contracts | Pending |  |
| All seven clause types found in each contract | Pending |  |
| Planted risks detected | Pending |  |
| Executive summaries readable | Pending |  |
| Clause comparison works across all contracts | Pending |  |
| Five chat questions answered per contract | Pending |  |
| UI screenshots captured | Pending |  |

