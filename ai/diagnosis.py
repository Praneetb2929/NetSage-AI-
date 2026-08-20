import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing.\n"
        "Create a .env file in the NetSage-AI folder and add:\n\n"
        "GROQ_API_KEY=your_api_key_here"
    )


# ============================================================
# 2. CREATE GROQ CLIENT
# ============================================================

client = Groq(api_key=API_KEY)


# ============================================================
# 3. MODEL CONFIGURATION
# ============================================================

MODEL_NAME = "openai/gpt-oss-20b"

MAX_ATTEMPTS = 3

MAX_COMPLETION_TOKENS = 1600

TEMPERATURE = 0.1


# ============================================================
# 4. LOAD DIAGNOSIS PROMPT
# ============================================================

def load_prompt():

    prompt_path = (
        Path(__file__).parent.parent
        / "prompts"
        / "diagnose_prompt.md"
    )

    if not prompt_path.exists():

        raise FileNotFoundError(
            f"Diagnosis prompt was not found at:\n{prompt_path}"
        )

    with open(
        prompt_path,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


# ============================================================
# 5. CLEAN AI RESPONSE
# ============================================================

def clean_response(answer):

    if answer is None:
        return ""

    answer = answer.strip()

    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

    if answer.startswith("```"):

        lines = answer.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        answer = "\n".join(lines).strip()

    return answer


# ============================================================
# 6. EXTRACT JSON FROM RESPONSE
# ============================================================

def extract_json(answer):

    if not answer:
        return None

    answer = clean_response(answer)

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        return json.loads(answer)

    except json.JSONDecodeError:

        pass

    # --------------------------------------------------------
    # Try to locate JSON object inside extra text
    # --------------------------------------------------------

    start = answer.find("{")
    end = answer.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    json_text = answer[start:end + 1]

    try:

        return json.loads(json_text)

    except json.JSONDecodeError:

        return None


# ============================================================
# 7. VALIDATE STRUCTURED DIAGNOSIS
# ============================================================

def validate_response(answer):

    if not answer:
        return False

    data = extract_json(answer)

    if not isinstance(data, dict):
        return False

    required_fields = [

        "root_cause",
        "confidence",
        "osi_layer",
        "evidence",
        "next_command",
        "fix_steps"

    ]

    for field in required_fields:

        if field not in data:
            return False

    # --------------------------------------------------------
    # Root cause
    # --------------------------------------------------------

    if not isinstance(
        data["root_cause"],
        str
    ):

        return False

    if len(
        data["root_cause"].strip()
    ) < 5:

        return False

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = data["confidence"]

    if isinstance(confidence, str):

        try:

            confidence = float(
                confidence.replace("%", "")
            )

            if confidence > 1:
                confidence = confidence / 100

        except ValueError:

            return False

    if not isinstance(
        confidence,
        (int, float)
    ):

        return False

    if not 0 <= confidence <= 1:

        return False

    # --------------------------------------------------------
    # OSI layer
    # --------------------------------------------------------

    if not isinstance(
        data["osi_layer"],
        str
    ):

        return False

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    if not isinstance(
        data["evidence"],
        list
    ):

        return False

    # --------------------------------------------------------
    # Next command
    # --------------------------------------------------------

    if not isinstance(
        data["next_command"],
        str
    ):

        return False

    # --------------------------------------------------------
    # Fix steps
    # --------------------------------------------------------

    if not isinstance(
        data["fix_steps"],
        list
    ):

        return False

    if len(data["fix_steps"]) == 0:

        return False

    return True


# ============================================================
# 8. NORMALIZE DIAGNOSIS
# ============================================================

def normalize_diagnosis(answer):

    data = extract_json(answer)

    if not data:
        return answer

    # --------------------------------------------------------
    # Normalize confidence
    # --------------------------------------------------------

    confidence = data.get(
        "confidence",
        0
    )

    try:

        if isinstance(confidence, str):

            confidence = float(
                confidence.replace("%", "")
            )

        confidence = float(confidence)

        if confidence > 1:

            confidence = confidence / 100

    except (ValueError, TypeError):

        confidence = 0

    confidence = max(
        0,
        min(1, confidence)
    )

    data["confidence"] = round(
        confidence,
        2
    )

    # --------------------------------------------------------
    # Ensure list fields are lists
    # --------------------------------------------------------

    for field in [
        "evidence",
        "fix_steps"
    ]:

        if not isinstance(
            data.get(field),
            list
        ):

            data[field] = [
                str(data.get(field, ""))
            ]

    # --------------------------------------------------------
    # Clean strings
    # --------------------------------------------------------

    for field in [
        "root_cause",
        "osi_layer",
        "next_command"
    ]:

        if field in data:

            data[field] = str(
                data[field]
            ).strip()

    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 9. BUILD CASE INFORMATION
# ============================================================

def build_case_information(
    case,
    rule_results=None
):

    case_information = f"""
CASE INFORMATION

Case ID:
{case.get("case_id")}

Symptom:
{case.get("symptom")}

Topology:
{case.get("topology_note")}

Show Command Evidence:
{case.get("show_output")}

Expected Fault:
{case.get("expected_fault")}

OSI Layer:
{case.get("osi_layer")}

Concept:
{case.get("concept")}

Severity:
{case.get("severity")}
"""

    # --------------------------------------------------------
    # Deterministic findings
    # --------------------------------------------------------

    if rule_results:

        case_information += f"""

DETERMINISTIC RULE CHECKER FINDINGS

{json.dumps(
    rule_results,
    indent=2,
    ensure_ascii=False
)}
"""

    else:

        case_information += """

DETERMINISTIC RULE CHECKER FINDINGS

No deterministic rule-checker findings were provided.
"""

    # --------------------------------------------------------
    # Strong reasoning constraints
    # --------------------------------------------------------

    case_information += """

============================================================
DIAGNOSIS RULES
============================================================

You are diagnosing a computer networking problem.

Follow these rules strictly.

RULE 1:
Use the actual Show Command Evidence as the primary source
of truth.

RULE 2:
Deterministic rule-checker findings are stronger evidence than
the Expected Fault field.

RULE 3:
The Expected Fault is only a hypothesis.
Do NOT automatically accept it.

RULE 4:
Never invent command output, IP addresses, interfaces,
VLANs, routes, ACLs, NAT translations, DNS servers,
or configuration states that are not present in the evidence.

RULE 5:
If a rule-checker finding explicitly FAILS, investigate that
finding carefully before selecting another root cause.

RULE 6:
If the evidence contradicts a possible root cause, do not
select that root cause.

RULE 7:
A successful configuration elsewhere does not automatically
prove that the affected device is correctly configured.

RULE 8:
If evidence is insufficient, say so explicitly.

RULE 9:
Confidence must reflect the strength of the evidence.

RULE 10:
Do not use the Expected Fault merely because it appears in
the case information.

============================================================
NETWORK REASONING
============================================================

Use appropriate networking logic.

For Layer 2 problems, consider:

- VLAN assignment
- access ports
- trunk configuration
- MAC learning
- interface status
- STP
- duplex/speed
- switchport configuration

For Layer 3 problems, consider:

- IP address
- subnet mask
- default gateway
- routing table
- static routes
- dynamic routing
- ARP
- interface status

For NAT problems, consider:

- inside/outside interfaces
- NAT rules
- ACL used by NAT
- translation table
- overload/PAT
- routing toward the ISP

For ACL problems, consider:

- source
- destination
- protocol
- direction
- interface
- permit/deny ordering

For DNS problems, distinguish:

- IP connectivity failure
- DNS resolution failure

For DHCP problems, consider:

- DHCP server
- address pool
- excluded addresses
- relay/helper configuration
- client lease
- VLAN reachability

============================================================
IMPORTANT
============================================================

Do not diagnose a Layer 3 gateway problem simply because
the user cannot reach the Internet.

First determine whether the evidence actually supports:

1. IP configuration failure
2. Gateway failure
3. Routing failure
4. NAT failure
5. ACL failure
6. DNS failure
7. Layer 2 failure

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not use markdown.

Do not put the JSON inside ```.

The JSON MUST contain exactly these fields:

{
    "root_cause": "string",
    "confidence": 0.0,
    "osi_layer": "string",
    "evidence": [
        "evidence item 1",
        "evidence item 2"
    ],
    "next_command": "string",
    "fix_steps": [
        "step 1",
        "step 2",
        "step 3"
    ]
}

============================================================
FIELD REQUIREMENTS
============================================================

root_cause:
Give one specific root cause.

confidence:
Use a number between 0.0 and 1.0.

osi_layer:
Give the most relevant OSI layer.

evidence:
List only evidence that supports the diagnosis.

next_command:
Give the single most useful command/check to confirm
the diagnosis.

fix_steps:
Give practical ordered steps.

If evidence is insufficient, root_cause should clearly state
that the evidence is insufficient and next_command should
identify the command needed to determine the actual cause.
"""


    return case_information


# ============================================================
# 10. REQUEST DIAGNOSIS FROM GROQ
# ============================================================

def request_diagnosis(
    base_prompt,
    case_information
):

    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[
            {
                "role": "system",
                "content": base_prompt
            },
            {
                "role": "user",
                "content": case_information
            }
        ],

        temperature=TEMPERATURE,

        max_completion_tokens=MAX_COMPLETION_TOKENS
    )

    # --------------------------------------------------------
    # Check choices
    # --------------------------------------------------------

    if not response.choices:

        raise RuntimeError(
            "Groq returned no choices."
        )

    message = response.choices[0].message

    if message is None:

        raise RuntimeError(
            "Groq returned no message."
        )

    # --------------------------------------------------------
    # Extract content
    # --------------------------------------------------------

    answer = clean_response(
        message.content
    )

    if not answer:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    return answer


# ============================================================
# 11. DIAGNOSE A NETWORK CASE
# ============================================================

def diagnose_case(
    case,
    rule_results=None
):

    base_prompt = load_prompt()

    case_information = build_case_information(
        case,
        rule_results
    )

    # --------------------------------------------------------
    # Retry mechanism
    # --------------------------------------------------------

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1
    ):

        try:

            print(
                f"AI request attempt "
                f"{attempt}/{MAX_ATTEMPTS}..."
            )

            answer = request_diagnosis(
                base_prompt,
                case_information
            )

            # ------------------------------------------------
            # Validate
            # ------------------------------------------------

            if validate_response(answer):

                print(
                    "AI diagnosis received "
                    "and validated successfully."
                )

                return normalize_diagnosis(
                    answer
                )

            print(
                "WARNING: AI returned an invalid "
                "diagnosis structure."
            )

            # ------------------------------------------------
            # Retry with stronger instruction
            # ------------------------------------------------

            if attempt < MAX_ATTEMPTS:

                print(
                    "Retrying with stricter JSON "
                    "requirements..."
                )

                case_information += """

IMPORTANT RETRY INSTRUCTION:

Your previous response did not satisfy the required
JSON structure.

Return ONLY valid JSON containing:

root_cause
confidence
osi_layer
evidence
next_command
fix_steps

Do not include markdown.
Do not include explanations outside the JSON.
"""

                time.sleep(1)

        except Exception as error:

            print(
                "\n========== GROQ ERROR =========="
            )

            print(error)

            print(
                "================================\n"
            )

            if attempt < MAX_ATTEMPTS:

                print(
                    "Retrying AI request..."
                )

                time.sleep(2)

            else:

                raise

    # --------------------------------------------------------
    # All attempts failed
    # --------------------------------------------------------

    raise RuntimeError(
        f"AI failed to return a valid diagnosis "
        f"for Case {case.get('case_id')} "
        f"after {MAX_ATTEMPTS} attempts."
    )


# ============================================================
# 12. TEST CASE
# ============================================================

if __name__ == "__main__":

    test_case = {

        "case_id": 1,

        "symptom":
            "PC cannot reach another device in the same VLAN",

        "topology_note":
            "PC1 connected to SW1 access port intended for VLAN 10.",

        "show_output":
            "show vlan brief\n"
            "VLAN 10: Fa0/2\n"
            "VLAN 20: Fa0/1\n"
            "PC1 is connected to Fa0/1.",

        "expected_fault":
            "PC1 access port is assigned to the wrong VLAN.",

        "osi_layer":
            "Layer 2",

        "concept":
            "VLAN",

        "severity":
            "High"
    }

    # --------------------------------------------------------
    # Example deterministic findings
    # --------------------------------------------------------

    test_rule_results = {

        "checks": [

            {
                "check": "vlan",
                "passed": False,
                "message":
                    "PC1 appears to be connected to "
                    "a port assigned to VLAN 20 instead "
                    "of VLAN 10.",
                "evidence": [
                    "Fa0/1 belongs to VLAN 20",
                    "PC1 is connected to Fa0/1",
                    "Expected VLAN is VLAN 10"
                ]
            }

        ]

    }

    print(
        "\n========================================"
    )

    print(
        "          NETSAGE AI TEST"
    )

    print(
        "========================================"
    )

    print(
        f"\nUsing model: {MODEL_NAME}"
    )

    print(
        "\nSending case to Groq..."
    )

    try:

        result = diagnose_case(
            test_case,
            test_rule_results
        )

        print(
            "\n========== AI DIAGNOSIS ==========\n"
        )

        print(result)

        print(
            "\n=================================="
        )

    except Exception as error:

        print(
            "\n========== DIAGNOSIS FAILED =========="
        )

        print(error)

        print(
            "======================================"
        )