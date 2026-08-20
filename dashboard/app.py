import streamlit as st
import sys
from pathlib import Path
import json
import csv
import re
from datetime import datetime


# ============================================================
# 1. PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 2. IMPORT NETSAGE AI
# ============================================================

from ai.diagnosis import diagnose_case


# ============================================================
# 3. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NetSage AI",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 4. OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

REVIEW_FILE = OUTPUT_DIR / "user_reviews.csv"


# ============================================================
# 5. CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- Main ---------- */

    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 18px;
        color: #9ca3af;
        margin-bottom: 25px;
    }

    /* ---------- Cards ---------- */

    .card {
        padding: 22px;
        border-radius: 14px;
        background-color: #151922;
        border: 1px solid #303642;
        margin-bottom: 18px;
    }

    .card-title {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 12px;
    }

    .root-cause {
        font-size: 24px;
        font-weight: 600;
        line-height: 1.45;
    }

    .confidence {
        font-size: 30px;
        font-weight: 800;
    }

    .evidence-item {
        padding: 7px 0;
        font-size: 16px;
        line-height: 1.5;
    }

    .fix-step {
        padding: 8px 0;
        font-size: 16px;
        line-height: 1.5;
    }

    /* ---------- Status ---------- */

    .status {
        padding: 10px 14px;
        border-radius: 10px;
        font-weight: 600;
        margin-bottom: 15px;
    }

    /* ---------- Footer ---------- */

    .footer {
        color: #777;
        text-align: center;
        padding: 25px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 6. SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "diagnosis": None,
    "raw_result": None,
    "case": None,
    "review_status": None,
    "review_saved": False,
}

for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 7. HELPER: RESET APPLICATION
# ============================================================

def reset_app():

    st.session_state.diagnosis = None
    st.session_state.raw_result = None
    st.session_state.case = None
    st.session_state.review_status = None
    st.session_state.review_saved = False


# ============================================================
# 8. PARSE AI RESPONSE
# ============================================================

def parse_ai_response(result):

    if not result:
        return None

    # --------------------------------------------------------
    # Attempt 1: direct JSON
    # --------------------------------------------------------

    if isinstance(result, dict):
        return result

    try:

        return json.loads(result)

    except (json.JSONDecodeError, TypeError):
        pass


    # --------------------------------------------------------
    # Attempt 2: remove markdown fences
    # --------------------------------------------------------

    cleaned = result.strip()

    if cleaned.startswith("```"):

        lines = cleaned.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

        try:

            return json.loads(cleaned)

        except json.JSONDecodeError:
            pass


    # --------------------------------------------------------
    # Attempt 3: extract JSON object
    # --------------------------------------------------------

    try:

        match = re.search(
            r"\{.*\}",
            cleaned,
            re.DOTALL
        )

        if match:

            return json.loads(match.group())

    except (json.JSONDecodeError, TypeError):
        pass


    return None


# ============================================================
# 9. SAVE HUMAN REVIEW
# ============================================================

def save_review(case, diagnosis, decision):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    file_exists = REVIEW_FILE.exists()

    row = {
        "timestamp": timestamp,
        "case_id": case.get("case_id", ""),
        "symptom": case.get("symptom", ""),
        "severity": case.get("severity", ""),
        "root_cause": diagnosis.get(
            "root_cause",
            ""
        ),
        "confidence": diagnosis.get(
            "confidence",
            ""
        ),
        "osi_layer": diagnosis.get(
            "osi_layer",
            ""
        ),
        "next_command": diagnosis.get(
            "next_command",
            ""
        ),
        "review_decision": decision,
    }

    fieldnames = [
        "timestamp",
        "case_id",
        "symptom",
        "severity",
        "root_cause",
        "confidence",
        "osi_layer",
        "next_command",
        "review_decision",
    ]

    with open(
        REVIEW_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


# ============================================================
# 10. DISPLAY DIAGNOSIS
# ============================================================

def display_diagnosis(diagnosis):

    st.divider()

    st.header("🧠 AI Diagnosis")


    # ========================================================
    # ROOT CAUSE
    # ========================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="card-title">🎯 Root Cause</div>',
        unsafe_allow_html=True
    )

    root_cause = diagnosis.get(
        "root_cause",
        "Not provided"
    )

    st.markdown(
        f'<div class="root-cause">{root_cause}</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # ========================================================
    # CONFIDENCE + OSI
    # ========================================================

    col1, col2 = st.columns(2)


    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    with col1:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="card-title">🎯 Confidence</div>',
            unsafe_allow_html=True
        )

        confidence = diagnosis.get(
            "confidence",
            0
        )

        try:

            confidence_value = float(
                confidence
            )

            if confidence_value > 1:
                confidence_value /= 100

            confidence_value = min(
                max(confidence_value, 0),
                1
            )

            confidence_percent = (
                confidence_value * 100
            )

            st.markdown(
                f'<div class="confidence">'
                f'{confidence_percent:.0f}%'
                f'</div>',
                unsafe_allow_html=True
            )

            st.progress(
                confidence_value
            )

        except (ValueError, TypeError):

            st.write(confidence)

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # --------------------------------------------------------
    # OSI Layer
    # --------------------------------------------------------

    with col2:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="card-title">🌐 OSI Layer</div>',
            unsafe_allow_html=True
        )

        osi_layer = diagnosis.get(
            "osi_layer",
            "Not provided"
        )

        st.markdown(
            f'<div class="confidence">'
            f'{osi_layer}'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )


    # ========================================================
    # EVIDENCE
    # ========================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="card-title">🔎 Evidence</div>',
        unsafe_allow_html=True
    )

    evidence = diagnosis.get(
        "evidence",
        []
    )

    if isinstance(evidence, list):

        if evidence:

            for item in evidence:

                st.markdown(
                    f'<div class="evidence-item">'
                    f'• {item}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        else:

            st.info(
                "No evidence was provided."
            )

    else:

        st.write(evidence)

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # ========================================================
    # NEXT COMMAND
    # ========================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="card-title">⌨️ Next Command</div>',
        unsafe_allow_html=True
    )

    command = diagnosis.get(
        "next_command",
        "Not provided"
    )

    st.code(
        command,
        language="text"
    )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


    # ========================================================
    # FIX STEPS
    # ========================================================

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="card-title">🛠️ Recommended Fix</div>',
        unsafe_allow_html=True
    )

    fix_steps = diagnosis.get(
        "fix_steps",
        []
    )

    if isinstance(fix_steps, list):

        if fix_steps:

            for index, step in enumerate(
                fix_steps,
                start=1
            ):

                st.markdown(
                    f'<div class="fix-step">'
                    f'<b>{index}.</b> {step}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        else:

            st.info(
                "No fix steps were provided."
            )

    else:

        st.write(fix_steps)

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# 11. HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🌐 NetSage AI'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-powered network troubleshooting assistant'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# 12. SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🌐 NetSage AI")

    st.write(
        "Network troubleshooting powered by "
        "AI + deterministic checks + human review."
    )

    st.divider()

    st.subheader("How it works")

    st.write(
        "1. Describe the problem"
    )

    st.write(
        "2. Provide network evidence"
    )

    st.write(
        "3. AI analyzes the case"
    )

    st.write(
        "4. Review the diagnosis"
    )

    st.write(
        "5. Save the final decision"
    )

    st.divider()

    if st.button(
        "🔄 New Diagnosis",
        use_container_width=True
    ):

        reset_app()
        st.rerun()

    st.divider()

    st.caption(
        "NetSage AI"
    )

    st.caption(
        "AI-assisted network troubleshooting"
    )


# ============================================================
# 13. INPUT SECTION
# ============================================================

st.header("🔍 Network Problem")

st.write(
    "Describe the problem and provide any available "
    "network evidence."
)


symptom = st.text_area(
    "Describe the network problem",
    placeholder=(
        "Example:\n"
        "One workstation cannot reach the internet "
        "while other workstations can."
    ),
    height=120
)


topology = st.text_area(
    "Topology / Network Context",
    placeholder=(
        "Example:\n"
        "PC1 → SW1 → R1 → Internet\n"
        "PC1 is connected to VLAN 10."
    ),
    height=100
)


show_output = st.text_area(
    "Show Command Output / Evidence",
    placeholder=(
        "Paste Cisco command output here.\n\n"
        "Example:\n"
        "show ip interface brief\n"
        "show ip route\n"
        "show access-lists\n"
        "show ip nat translations"
    ),
    height=220
)


severity = st.selectbox(
    "Severity",
    [
        "Low",
        "Medium",
        "High",
        "Critical"
    ]
)


# ============================================================
# 14. DIAGNOSE BUTTON
# ============================================================

if st.button(
    "🚀 Diagnose Network Problem",
    type="primary",
    use_container_width=True
):

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not symptom.strip():

        st.warning(
            "Please describe the network problem first."
        )

        st.stop()


    # --------------------------------------------------------
    # Create case ID
    # --------------------------------------------------------

    case_id = (
        "USER-"
        + datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )
    )


    # --------------------------------------------------------
    # Build case
    # --------------------------------------------------------

    case = {

        "case_id":
            case_id,

        "symptom":
            symptom.strip(),

        "topology_note":
            topology.strip()
            if topology.strip()
            else "Not provided",

        "show_output":
            show_output.strip()
            if show_output.strip()
            else "No command output provided",

        "expected_fault":
            "Unknown - determine from evidence",

        "osi_layer":
            "Unknown - determine from evidence",

        "concept":
            "Unknown - determine from evidence",

        "severity":
            severity
    }


    # --------------------------------------------------------
    # Reset old diagnosis
    # --------------------------------------------------------

    st.session_state.diagnosis = None
    st.session_state.raw_result = None
    st.session_state.review_status = None
    st.session_state.review_saved = False
    st.session_state.case = case


    # --------------------------------------------------------
    # Run AI
    # --------------------------------------------------------

    with st.spinner(
        "🧠 NetSage AI is analyzing the network..."
    ):

        try:

            result = diagnose_case(
                case
            )

            st.session_state.raw_result = result


            # ------------------------------------------------
            # Parse response
            # ------------------------------------------------

            diagnosis = parse_ai_response(
                result
            )


            # ------------------------------------------------
            # Validate structured response
            # ------------------------------------------------

            if diagnosis is None:

                st.error(
                    "AI returned a response, but it could "
                    "not be converted into JSON."
                )

                st.subheader(
                    "Raw AI Response"
                )

                st.code(
                    result,
                    language="text"
                )

                st.stop()


            # ------------------------------------------------
            # Store diagnosis
            # ------------------------------------------------

            st.session_state.diagnosis = diagnosis

            st.success(
                "✅ Diagnosis generated successfully."
            )

        except Exception as error:

            st.error(
                "❌ NetSage AI encountered an error."
            )

            st.exception(error)


# ============================================================
# 15. DISPLAY DIAGNOSIS
# ============================================================

if st.session_state.diagnosis:

    diagnosis = st.session_state.diagnosis

    case = st.session_state.case

    display_diagnosis(
        diagnosis
    )


    # ========================================================
    # HUMAN REVIEW
    # ========================================================

    st.divider()

    st.header("👨‍💻 Human Review")

    st.write(
        "Review the AI diagnosis before accepting it."
    )

    st.caption(
        f"Case ID: {case.get('case_id', 'Unknown')}"
    )


    # --------------------------------------------------------
    # Already reviewed
    # --------------------------------------------------------

    if st.session_state.review_status:

        status = st.session_state.review_status

        if status == "Approved":

            st.success(
                "✅ Diagnosis approved and saved."
            )

        elif status == "Rejected":

            st.error(
                "❌ Diagnosis rejected and saved."
            )

        elif status == "Needs Correction":

            st.warning(
                "⚠️ Diagnosis marked as needing correction."
            )


    # --------------------------------------------------------
    # Review buttons
    # --------------------------------------------------------

    else:

        review_col1, review_col2, review_col3 = (
            st.columns(3)
        )


        # ====================================================
        # APPROVE
        # ====================================================

        with review_col1:

            if st.button(
                "✅ Approve",
                use_container_width=True
            ):

                save_review(
                    case,
                    diagnosis,
                    "Approved"
                )

                st.session_state.review_status = (
                    "Approved"
                )

                st.session_state.review_saved = True

                st.rerun()


        # ====================================================
        # REJECT
        # ====================================================

        with review_col2:

            if st.button(
                "❌ Reject",
                use_container_width=True
            ):

                save_review(
                    case,
                    diagnosis,
                    "Rejected"
                )

                st.session_state.review_status = (
                    "Rejected"
                )

                st.session_state.review_saved = True

                st.rerun()


        # ====================================================
        # NEEDS CORRECTION
        # ====================================================

        with review_col3:

            if st.button(
                "⚠️ Needs Correction",
                use_container_width=True
            ):

                save_review(
                    case,
                    diagnosis,
                    "Needs Correction"
                )

                st.session_state.review_status = (
                    "Needs Correction"
                )

                st.session_state.review_saved = True

                st.rerun()


    # ========================================================
    # REVIEW FILE
    # ========================================================

    if st.session_state.review_saved:

        st.info(
            f"Human review saved to:\n{REVIEW_FILE}"
        )


# ============================================================
# 16. FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="footer">
        NetSage AI — AI-assisted network troubleshooting
        with human oversight
    </div>
    """,
    unsafe_allow_html=True
)