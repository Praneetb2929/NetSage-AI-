
Readme · MD
# 🌐 NetSage AI
 
AI-assisted network troubleshooting system that combines LLM-based diagnosis, deterministic network rule checking, and human review.
 
## 🚀 Overview
 
NetSage AI helps diagnose network problems using:
 
- 🤖 AI-powered diagnosis
- 🔍 Deterministic rule-based checks
- 🌐 Network evidence analysis
- 🧑‍💻 Human-in-the-loop review
- 📊 CSV-based result and review storage
The system is designed to **assist** network engineers rather than replace human decision-making.
 
## 🏗️ Architecture
 
```
User
  ↓
Streamlit Dashboard
  ↓
Network Problem + Evidence
  ↓
Rule Checker
  ↓
AI Diagnosis
  ↓
Diagnosis + Confidence + Evidence
  ↓
Human Review
  ↓
Approved / Rejected / Needs Correction
  ↓
CSV Output
```
 
## 📁 Project Structure
 
```text
NetSage-AI/
├── ai/
│   └── diagnosis.py
├── checker/
│   └── rule_checker.py
├── dashboard/
│   └── app.py
├── data/
│   └── cases.csv
├── outputs/
├── prompts/
│   └── diagnose_prompt.md
├── main.py
├── review.py
├── run_cases.py
├── requirements.txt
└── README.md
```
 
## ✨ Features
 
### AI Diagnosis
 
The system sends network cases and collected evidence to an LLM for diagnosis. The AI returns:
 
- Root cause
- Confidence
- OSI layer
- Evidence
- Next troubleshooting command
- Recommended fix steps
### Deterministic Rule Checker
 
Rule-based checks validate network evidence for issues such as:
 
- VLAN configuration
- Interface status
- Routing
- NAT
- ACL
- DHCP
- DNS
- Wireless configuration
This provides an additional layer of verification instead of relying only on the LLM.
 
### Human Review
 
A human reviewer can:
 
- Approve the diagnosis
- Reject the diagnosis
- Mark it as needing correction
The review decision is stored for later analysis.
 
## 🖥️ Dashboard
 
Run the Streamlit dashboard:
 
```bash
streamlit run dashboard/app.py
```
 
Then open: [http://localhost:8501](http://localhost:8501)
 
## ⚙️ Installation
 
Clone the repository:
 
```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd NetSage-AI
```
 
Create a virtual environment:
 
```bash
python -m venv .venv
```
 
Activate it on Windows:
 
```bash
.venv\Scripts\activate
```
 
Install dependencies:
 
```bash
pip install -r requirements.txt
```
 
Create a `.env` file:
 
```env
GROQ_API_KEY=your_api_key_here
```
 
## ▶️ Running the Project
 
Run AI diagnosis:
 
```bash
python ai/diagnosis.py
```
 
Run the dashboard:
 
```bash
streamlit run dashboard/app.py
```
 
## 📊 Output
 
The system stores results in CSV files:
 
```text
outputs/
├── ai_results.csv
├── reviewed_results.csv
└── user_reviews.csv
```
 
These contain AI-generated diagnoses and human review decisions.
 
## 🧪 Example Diagnosis
 
```json
{
  "root_cause": "PC1 access port is assigned to the wrong VLAN",
  "confidence": 0.98,
  "osi_layer": "Layer 2",
  "next_command": "show interfaces Fa0/1 switchport"
}
```
 
The system can identify that PC1 is connected to an incorrect VLAN and recommend the appropriate Cisco troubleshooting command.
 
## 🧠 Human-in-the-Loop
 
NetSage AI does not automatically apply network configuration changes. The AI provides a diagnosis and recommended remediation steps, which must be reviewed by a human before acceptance.
 
## 🛠️ Technologies
 
- Python
- Streamlit
- Groq API
- LLM
- Pandas
- Cisco networking concepts
- Rule-based validation
- CSV-based data storage

## 👨‍💻 Author
Praneet Biswal