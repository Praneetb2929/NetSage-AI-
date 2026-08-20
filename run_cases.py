"""
NetSage AI - Run All Cases
Reads data/cases.csv, runs deterministic checks, sends each case
to the AI, and saves results to outputs/ai_results.csv.
"""

import csv
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai.diagnosis import diagnose_case
from checker.rule_checker import run_checks


DATA_FILE = PROJECT_ROOT / "data" / "cases.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "ai_results.csv"


def load_cases():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Cases file was not found:\n{DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8-sig", newline="") as file:
        cases = list(csv.DictReader(file))

    if not cases:
        raise ValueError("No cases were found in cases.csv.")

    return cases


def save_results(results):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "case_id",
        "symptom",
        "concept",
        "severity",
        "rule_checker_results",
        "ai_diagnosis",
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def process_case(case):
    rule_results = run_checks(case)

    print(f"\nCase {case.get('case_id')}: {case.get('symptom')}")

    if rule_results:
        print("Rule checker:")
        for check in rule_results:
            status = "PASS" if check["passed"] else "FLAG"
            print(f"  [{status}] {check['message']}")
    else:
        print("Rule checker: No structured inputs available.")

    print("Sending case to AI...")

    try:
        ai_result = diagnose_case(case, rule_results=rule_results)
        print("AI diagnosis received.")
    except Exception as error:
        print(f"AI diagnosis failed: {error}")
        ai_result = json.dumps({"error": str(error)})

    return {
        "case_id": case.get("case_id"),
        "symptom": case.get("symptom"),
        "concept": case.get("concept"),
        "severity": case.get("severity"),
        "rule_checker_results": json.dumps(
            rule_results, ensure_ascii=False
        ),
        "ai_diagnosis": ai_result,
    }


def main():
    print("\n==========================================")
    print("       NETSAGE AI - CASE RUNNER")
    print("==========================================")

    cases = load_cases()

    print(f"\nLoaded {len(cases)} cases.")
    print(f"Output: {OUTPUT_FILE}")

    results = []

    for index, case in enumerate(cases, start=1):
        print("\n------------------------------------------")
        print(f"Processing {index}/{len(cases)}")
        print("------------------------------------------")

        results.append(process_case(case))

        if index < len(cases):
            time.sleep(1)

    save_results(results)

    print("\n==========================================")
    print("             COMPLETED")
    print("==========================================")
    print(f"\nProcessed cases: {len(results)}")
    print(f"Results saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    main()