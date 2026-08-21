# Health-Care-Assistant: Mobile-Ready Healthcare LLM & RAG Microservice

An enterprise-ready, multi-agent **Healthcare Knowledge Navigator & RAG Chatbot Service** built with FastAPI, Scikit-learn TF-IDF RAG, pluggable LLM provider engine (Ollama / Anthropic / OpenAI / Gemini / Template), emergency red-flag safety triage, multi-turn clinical context memory, auto-escalation ticket management, mobile REST API router, and a React + Vite web dashboard.

---

## 🌟 Key Features

- **Mobile API Layer**: Dedicated lightweight REST endpoints (`/mobile/api/chat`, `/mobile/api/triage`, `/mobile/api/config`) with expanded CORS support for mobile webviews (`capacitor://localhost`), iOS, Android Emulator (`10.0.2.2`), and React Native apps (e.g., CarePulse).
- **Zero-GPU Clinical RAG Engine**: Instant document grounding using TF-IDF + Cosine Similarity over medical guidelines (`.md`, `.txt`, `.pdf`). Automatically parses, chunks, and indexes documents.
- **Emergency Safety Triage**: Real-time red-flag symptom classifier (EMERGENCY / URGENT_EVALUATION / ROUTINE_CONSULTATION / GENERAL_INFO). Instantly overrides LLM generation with 911 / ER guidance for critical conditions (e.g. chest pain, stroke, severe distress).
- **Multi-Turn Patient Context Memory**: Dynamically extracts and maintains patient clinical context (age, sex, symptoms, duration, medications, lab values) across multi-turn chat sessions.
- **Follow-Up Question Agent**: Intelligently identifies missing clinical context and presents mobile quick-answer option chips.
- **Traceable Citations & Evidence Confidence**: Calculates evidence confidence (HIGH / MEDIUM / LOW) and returns structured source citations.
- **Pluggable LLM Layer**: Zero-code switching between `template` (zero-setup offline fallback), `ollama` (local Llama 3.2), `anthropic` (Claude 3.5), `openai` (GPT-4o-mini), and `gemini` (Gemini Flash).

---

## 📱 Mobile Integration (CarePulse / React Native / Capacitor)

See **[MOBILE_INTEGRATION.md](file:///c:/Users/Monish%20JB/OneDrive/Desktop/RAG_ChatBot/MOBILE_INTEGRATION.md)** for developer instructions and use the pre-built JavaScript SDK helper at [`frontend/src/api/mobileClient.js`](file:///c:/Users/Monish%20JB/OneDrive/Desktop/RAG_ChatBot/frontend/src/api/mobileClient.js):

```javascript
import { MobileHealthCopilot } from './mobileClient';

const copilot = new MobileHealthCopilot({ baseUrl: 'http://10.0.2.2:8000' });
copilot.setAuthToken(userToken);

// Rapid Standalone Triage Evaluation
const triage = await copilot.checkTriage("Sudden severe chest pain and arm numbness");

// Mobile Chat Message
const response = await copilot.sendChatMessage("What are the diagnostic criteria for primary hypothyroidism?");
```

---

## 🛠 Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, SQLite (swappable to PostgreSQL via `DATABASE_URL`), PyJWT, bcrypt, Scikit-learn, PyPDF, Uvicorn.
- **Frontend**: React 18, Vite, React Router v6, Recharts, Lucide React, Axios.
- **Containerization**: Docker, Docker Compose.

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```
- **Backend API**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
- **Frontend Application**: `http://localhost:5173`

---

## 🧪 Automated Verification Suite

Run all automated test suites to verify backend health, mobile APIs, multi-agent triage, and system E2E:

```bash
python backend/test_mobile_api.py
python backend/smoke_test.py
python backend/test_e2e.py
python backend/test_e2e_medical.py
```
