"""
Pruebas M1–M5 vía API HTTP (servidor uvicorn debe estar corriendo).
    .venv\\Scripts\\python.exe tests/run_memory_tests.py
"""
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.scenarios import MEMORY_SCENARIOS, MEMORY_TEST_USER_PREFIX

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = ROOT / "logs" / "validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _memory_texts(results: list[dict]) -> str:
    parts = []
    for item in results:
        text = item.get("memory") or item.get("text") or item.get("content") or ""
        parts.append(str(text).lower())
    return " ".join(parts)


def run_memory_tests() -> list[dict]:
    rows: list[dict] = []

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        try:
            client.get("/")
        except httpx.ConnectError:
            print("ERROR: Servidor no disponible. Arranca: uvicorn main:app --port 8000")
            sys.exit(1)

        for test_id, scenario in MEMORY_SCENARIOS.items():
            user_id = f"{MEMORY_TEST_USER_PREFIX}{test_id[1:]}"
            client.delete(f"/memories/{user_id}")
            time.sleep(0.5)

            client.post(
                f"/memories/{user_id}",
                json={"messages": scenario["store_messages"]},
            )
            time.sleep(3)

            resp = client.get(
                f"/memories/{user_id}/search",
                params={"q": scenario["query"], "limit": 5},
            )
            data = resp.json()
            memories = data.get("results", [])
            blob = _memory_texts(memories)
            hits = [kw for kw in scenario["must_contain"] if kw.lower() in blob]
            passed = len(hits) >= 1

            rows.append({
                "test_id": test_id,
                "name": scenario["name"],
                "query": scenario["query"],
                "stored_info": scenario["store_messages"][0]["content"][:80],
                "memories_found": len(memories),
                "recovered_text": blob[:200],
                "keywords_hit": ", ".join(hits),
                "passed": passed,
                "result": "PASS" if passed else "FAIL",
            })

    return rows


def write_report(rows: list[dict]) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"memory_validation_{ts}.csv"
    json_path = OUTPUT_DIR / f"memory_validation_{ts}.json"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    pct = (passed / total * 100) if total else 0

    print("\n=== Tabla 6 — Pruebas de persistencia contextual (Mem0) ===\n")
    print(f"{'Prueba':<8} {'Nombre':<28} {'Resultado':<8} {'Keywords'}")
    print("-" * 70)
    for r in rows:
        print(f"{r['test_id']:<8} {r['name']:<28} {r['result']:<8} {r['keywords_hit'] or '—'}")
    print("-" * 70)
    print(f"Coincidencia: {passed}/{total} ({pct:.1f}%)")
    print(f"\nReportes: {csv_path}\n           {json_path}")


def main() -> None:
    rows = run_memory_tests()
    write_report(rows)


if __name__ == "__main__":
    main()
