#!/usr/bin/env python3
"""End-to-end API checks for the Lai contract analysis pipeline.

Prerequisites:
  1. Start PostgreSQL: docker compose up -d
  2. Start backend with GEMINI_API_KEY configured:
     cd backend && uvicorn app.main:app --reload
  3. Run from repo root:
     python tests/e2e_api_check.py

The script uploads the sample contracts, triggers analysis, verifies target
clause extraction, checks planted risk signals, compares clauses across all
contracts, and asks five chat questions per contract.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "test-contracts"

CLAUSE_TYPES = {
    "indemnity",
    "limitation_of_liability",
    "governing_law",
    "termination",
    "ip_ownership",
    "payment_terms",
    "confidentiality",
}

SAMPLES = [
    {
        "path": CONTRACT_DIR / "standard_nda.docx",
        "expected_level": {"low", "medium"},
        "risk_terms": ["mutual", "maximum aggregate liability", "30 days written notice"],
    },
    {
        "path": CONTRACT_DIR / "risky_saas.docx",
        "expected_level": {"medium", "high", "critical"},
        "risk_terms": ["unlimited liability", "no cap on damages", "sole discretion"],
    },
    {
        "path": CONTRACT_DIR / "employment_contract.docx",
        "expected_level": {"high", "critical"},
        "risk_terms": ["unlimited liability", "irrevocably assigns all intellectual property", "immediately without cause"],
    },
]

CHAT_QUESTIONS = [
    "What are the top three risks in this contract?",
    "Who carries the indemnity risk?",
    "Does the contract include a liability cap?",
    "How can the contract be terminated?",
    "Summarize the confidentiality obligation in plain English.",
]


class E2EFailure(AssertionError):
    """Raised when an E2E expectation is not met."""


def request_json(
    method: str,
    url: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> Any:
    req = Request(url, data=body, method=method, headers=headers or {})
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise E2EFailure(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise E2EFailure(f"{method} {url} failed: {exc.reason}") from exc


def upload_contract(base_url: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        raise E2EFailure(f"Missing sample contract: {path}")

    boundary = f"----lai-e2e-{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            path.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return request_json(
        "POST",
        f"{base_url}/api/contracts/upload",
        payload,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def wait_for_analysis(base_url: str, contract_id: str, timeout_seconds: int) -> dict[str, Any]:
    request_json("POST", f"{base_url}/api/contracts/{contract_id}/analyze")
    deadline = time.time() + timeout_seconds
    last_status: dict[str, Any] = {}

    while time.time() < deadline:
        last_status = request_json("GET", f"{base_url}/api/contracts/{contract_id}/status")
        status = last_status.get("status")
        if status == "complete":
            return last_status
        if status == "error":
            raise E2EFailure(f"Analysis failed for {contract_id}: {last_status}")
        time.sleep(5)

    raise E2EFailure(f"Timed out waiting for analysis of {contract_id}. Last status: {last_status}")


def assert_clause_coverage(filename: str, clauses: list[dict[str, Any]]) -> None:
    found = {clause.get("clause_type") for clause in clauses}
    missing = sorted(CLAUSE_TYPES - found)
    if missing:
        raise E2EFailure(f"{filename} missing target clause types: {', '.join(missing)}")


def assert_planted_terms_detectable(filename: str, clauses: list[dict[str, Any]], terms: list[str]) -> None:
    extracted_text = "\n".join(clause.get("original_text") or "" for clause in clauses).lower()
    missing = [term for term in terms if term.lower() not in extracted_text]
    if missing:
        raise E2EFailure(f"{filename} did not preserve planted terms: {', '.join(missing)}")


def assert_summary_readable(base_url: str, contract_id: str, filename: str) -> None:
    summary = request_json("GET", f"{base_url}/api/contracts/{contract_id}/summary")
    text = json.dumps(summary)
    if len(text) < 200:
        raise E2EFailure(f"{filename} summary is too short to be useful")


def assert_chat(base_url: str, contract_id: str, filename: str) -> list[dict[str, Any]]:
    responses = []
    for question in CHAT_QUESTIONS:
        payload = json.dumps({"message": question}).encode("utf-8")
        response = request_json(
            "POST",
            f"{base_url}/api/contracts/{contract_id}/chat",
            payload,
            {"Content-Type": "application/json"},
        )
        answer = response.get("response", "")
        if len(answer.strip()) < 40:
            raise E2EFailure(f"{filename} chat answer too short for question: {question}")
        responses.append({"question": question, "response": answer})
    return responses


def compare_clause_type(base_url: str, contract_ids: list[str], clause_type: str) -> dict[str, Any]:
    payload = json.dumps({"contract_ids": contract_ids, "clause_type": clause_type}).encode("utf-8")
    result = request_json(
        "POST",
        f"{base_url}/api/compare",
        payload,
        {"Content-Type": "application/json"},
    )
    if len(result.get("comparisons", [])) != len(contract_ids):
        raise E2EFailure(
            f"Expected {len(contract_ids)} {clause_type} comparisons, got {len(result.get('comparisons', []))}"
        )
    return result


def run(base_url: str, timeout_seconds: int) -> dict[str, Any]:
    request_json("GET", f"{base_url}/api/health")
    uploaded: list[dict[str, Any]] = []
    report: dict[str, Any] = {"contracts": [], "comparisons": {}}

    for sample in SAMPLES:
        path = sample["path"]
        contract = upload_contract(base_url, path)
        contract_id = contract["id"]
        uploaded.append(contract)

        wait_for_analysis(base_url, contract_id, timeout_seconds)
        detail = request_json("GET", f"{base_url}/api/contracts/{contract_id}")
        clauses = request_json("GET", f"{base_url}/api/contracts/{contract_id}/clauses")

        assert_clause_coverage(path.name, clauses)
        assert_planted_terms_detectable(path.name, clauses, sample["risk_terms"])
        assert_summary_readable(base_url, contract_id, path.name)
        chat_responses = assert_chat(base_url, contract_id, path.name)

        risk_level = detail.get("risk_level")
        if risk_level not in sample["expected_level"]:
            raise E2EFailure(
                f"{path.name} expected risk level in {sorted(sample['expected_level'])}, got {risk_level}"
            )

        report["contracts"].append(
            {
                "filename": path.name,
                "contract_id": contract_id,
                "risk_level": risk_level,
                "overall_risk_score": detail.get("overall_risk_score"),
                "clause_types": sorted({clause.get("clause_type") for clause in clauses}),
                "chat_checked": len(chat_responses),
            }
        )

    contract_ids = [contract["id"] for contract in uploaded]
    for clause_type in sorted(CLAUSE_TYPES):
        report["comparisons"][clause_type] = compare_clause_type(base_url, contract_ids, clause_type)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Lai E2E API checks.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=600, help="Seconds to wait per analysis")
    args = parser.parse_args()

    try:
        report = run(args.base_url.rstrip("/"), args.timeout)
    except E2EFailure as exc:
        print(f"E2E FAILED: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    print("E2E PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
