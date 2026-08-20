"""
NetSage AI - Human Review System

Reads AI diagnoses from:
    outputs/ai_results.csv

Allows a human reviewer to:
    1. Approve
    2. Reject
    3. Mark as Needs Correction

The reviewer can also add a comment.

Final reviewed results are saved to:
    outputs/reviewed_results.csv
"""

import csv
import json
from pathlib import Path


# ============================================================
# FILE LOCATIONS
# ============================================================

PROJECT_ROOT = Path(__file__).parent

INPUT_FILE = PROJECT_ROOT / "outputs" / "ai_results.csv"

OUTPUT_FILE = PROJECT_ROOT / "outputs" / "reviewed_results.csv"


# ============================================================
# LOAD RESULTS
# ============================================================

def load_results():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"\nCould not find:\n{INPUT_FILE}\n\n"
            "Run this first:\n"
            "python run_cases.py\n"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


# ============================================================
# FORMAT AI DIAGNOSIS
# ============================================================

def display_diagnosis(ai_diagnosis):

    try:

        data = json.loads(ai_diagnosis)

    except (json.JSONDecodeError, TypeError):

        print("\nAI DIAGNOSIS:")
        print(ai_diagnosis)
        return

    print("\n========== AI DIAGNOSIS ==========")

    print(
        f"\nRoot Cause:\n"
        f"  {data.get('root_cause', 'Not provided')}"
    )

    print(
        f"\nConfidence:\n"
        f"  {data.get('confidence', 'Not provided')}"
    )

    print(
        f"\nOSI Layer:\n"
        f"  {data.get('osi_layer', 'Not provided')}"
    )

    evidence = data.get("evidence", [])

    print("\nEvidence:")

    if evidence:

        for item in evidence:
            print(f"  - {item}")

    else:
        print("  No evidence provided.")

    print(
        f"\nNext Command:\n"
        f"  {data.get('next_command', 'Not provided')}"
    )

    fix_steps = data.get("fix_steps", [])

    print("\nFix Steps:")

    if fix_steps:

        for index, step in enumerate(
            fix_steps,
            start=1
        ):

            print(f"  {index}. {step}")

    else:

        print("  No fix steps provided.")

    print("\n==================================")


# ============================================================
# DISPLAY RULE CHECKER
# ============================================================

def display_rule_results(rule_results):

    print("\n========== RULE CHECKER ==========")

    try:

        checks = json.loads(rule_results)

    except (json.JSONDecodeError, TypeError):

        print(rule_results)
        print("==================================")
        return

    for check in checks:

        status = (
            "FLAG"
            if not check.get("passed", True)
            else "PASS"
        )

        print(
            f"\n[{status}] "
            f"{check.get('check', 'unknown')}"
        )

        print(
            f"  {check.get('message', '')}"
        )

        evidence = check.get("evidence", [])

        if evidence:

            print("  Evidence:")

            for item in evidence:

                print(f"    - {item}")

    print("\n==================================")


# ============================================================
# GET REVIEW DECISION
# ============================================================

def get_review_decision():

    while True:

        print("\nChoose review decision:")

        print("  1. Approve")
        print("  2. Reject")
        print("  3. Needs Correction")

        choice = input(
            "\nYour choice (1/2/3): "
        ).strip()

        if choice == "1":

            return "Approved"

        if choice == "2":

            return "Rejected"

        if choice == "3":

            return "Needs Correction"

        print(
            "\nInvalid choice. "
            "Please enter 1, 2 or 3."
        )


# ============================================================
# GET REVIEW COMMENT
# ============================================================

def get_review_comment():

    print(
        "\nReviewer comment "
        "(press Enter to leave empty):"
    )

    return input("> ").strip()


# ============================================================
# SAVE REVIEWED RESULTS
# ============================================================

def save_results(results):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "case_id",
        "symptom",
        "concept",
        "severity",
        "rule_checker_results",
        "ai_diagnosis",
        "review_decision",
        "review_comment",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(results)


# ============================================================
# REVIEW ONE CASE
# ============================================================

def review_case(case, number, total):

    print("\n\n")
    print("=" * 60)

    print(
        f"CASE {number}/{total}"
    )

    print("=" * 60)

    print(
        f"\nCase ID:\n"
        f"  {case.get('case_id', '')}"
    )

    print(
        f"\nSymptom:\n"
        f"  {case.get('symptom', '')}"
    )

    print(
        f"\nConcept:\n"
        f"  {case.get('concept', '')}"
    )

    print(
        f"\nSeverity:\n"
        f"  {case.get('severity', '')}"
    )

    # --------------------------------------------------------
    # RULE CHECKER
    # --------------------------------------------------------

    display_rule_results(
        case.get(
            "rule_checker_results",
            ""
        )
    )

    # --------------------------------------------------------
    # AI DIAGNOSIS
    # --------------------------------------------------------

    display_diagnosis(
        case.get(
            "ai_diagnosis",
            ""
        )
    )

    # --------------------------------------------------------
    # HUMAN DECISION
    # --------------------------------------------------------

    decision = get_review_decision()

    comment = get_review_comment()

    case["review_decision"] = decision

    case["review_comment"] = comment

    print(
        f"\nSaved review: {decision}"
    )

    return case


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 60)

    print(
        "             NETSAGE AI"
    )

    print(
        "          HUMAN REVIEW"
    )

    print("=" * 60)

    try:

        cases = load_results()

    except FileNotFoundError as error:

        print(error)

        return

    if not cases:

        print(
            "\nNo AI results were found."
        )

        return

    print(
        f"\nLoaded {len(cases)} AI diagnoses."
    )

    print(
        "\nYou will review each case one by one."
    )

    print(
        "\nPress Enter to start..."
    )

    input()

    reviewed_cases = []

    for index, case in enumerate(
        cases,
        start=1
    ):

        reviewed_case = review_case(
            case,
            index,
            len(cases)
        )

        reviewed_cases.append(
            reviewed_case
        )

    save_results(
        reviewed_cases
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    approved = sum(
        1
        for case in reviewed_cases
        if case.get("review_decision")
        == "Approved"
    )

    rejected = sum(
        1
        for case in reviewed_cases
        if case.get("review_decision")
        == "Rejected"
    )

    corrections = sum(
        1
        for case in reviewed_cases
        if case.get("review_decision")
        == "Needs Correction"
    )

    print("\n")
    print("=" * 60)

    print(
        "             REVIEW COMPLETE"
    )

    print("=" * 60)

    print(
        f"\nTotal cases:       {len(reviewed_cases)}"
    )

    print(
        f"Approved:          {approved}"
    )

    print(
        f"Rejected:          {rejected}"
    )

    print(
        f"Needs Correction:  {corrections}"
    )

    print(
        f"\nResults saved to:"
        f"\n{OUTPUT_FILE}"
    )

    print("\n")


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":

    main()