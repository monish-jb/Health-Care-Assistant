# Mobile App Integration Guide (CarePulse / React Native / Capacitor / iOS / Android)

This guide documents how mobile applications (e.g. **CarePulse**, React Native, Capacitor, Ionic, Flutter, Swift iOS, or Android Kotlin apps) can seamlessly connect to this **Healthcare Knowledge Navigator & RAG Chatbot Engine** as a plug-and-play AI microservice.

---

## 1. Architecture Overview

```
 ┌────────────────────────────────────────────────────────┐
 │           Mobile Patient App (e.g. CarePulse)         │
 └───────────────────────────┬────────────────────────────┘
                             │ REST (HTTPS / JSON + JWT)
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │      Healthcare Knowledge Navigator LLM RAG Service     │
 ├────────────────────────────────────────────────────────┤
 │ • Mobile API Router      (/mobile/api/chat)            │
 │ • Rapid Standalone Triage(/mobile/api/triage)          │
 │ • Zero-GPU RAG Engine   (TF-IDF + Cosine Similarity)  │
 │ • Multi-Agent Pipeline   (Safety, Context, Confidence) │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Base Server URLs

- **Local Dev / Emulator Host**:
  - Android Emulator: `http://10.0.2.2:8000`
  - iOS Simulator / Local Dev: `http://localhost:8000` or `http://127.0.0.1:8000`
- **Production Server**: Deploy via Docker Compose or cloud host (e.g., Render, Railway, AWS).

---

## 3. Core Mobile Endpoints

### 3.1 Handshake & Capability Check
- **Endpoint**: `GET /mobile/api/config`
- **Response**:
```json
{
  "app_name": "Health-Care-Assistant LLM RAG Service",
  "version": "1.0.0",
  "llm_provider": "template",
  "rag_active": true,
  "total_kb_documents": 6,
  "emergency_triage_enabled": true
}
```

### 3.2 Standalone Rapid Symptom Triage Screen
- **Endpoint**: `POST /mobile/api/triage`
- **Request**:
```json
{
  "symptoms": "Severe chest pain and numbness in left arm"
}
```
- **Response**:
```json
{
  "triage_level": "EMERGENCY",
  "is_emergency": true,
  "recommended_action": "Call emergency services (911/112) or go to nearest Emergency Room immediately.",
  "message": "EMERGENCY ALERT: Severe symptoms detected..."
}
```

### 3.3 Mobile Chat Session with RAG & Context
- **Endpoint**: `POST /mobile/api/chat`
- **Headers**: `Authorization: Bearer <JWT_ACCESS_TOKEN>`
- **Request**:
```json
{
  "conversation_id": null,
  "content": "My father is 62 and experiencing fatigue for 2 weeks."
}
```
- **Response**:
```json
{
  "conversation_id": 42,
  "role": "assistant",
  "reply": "Chronic fatigue in adults requires evaluating thyroid function and serum glucose...",
  "intent": "symptom_question",
  "triage_level": "ROUTINE_CONSULTATION",
  "confidence_level": "MEDIUM",
  "is_emergency": false,
  "followup_options": ["1-3 days", "1-2 weeks", "More than 1 month"],
  "citations_count": 4,
  "response_time_ms": 120
}
```

---

## 4. Mobile SDK Client (`mobileClient.js`)

A ready-to-use JavaScript/TypeScript client helper is provided at [`frontend/src/api/mobileClient.js`](file:///c:/Users/Monish%20JB/OneDrive/Desktop/RAG_ChatBot/frontend/src/api/mobileClient.js) for easy integration into React Native or Capacitor mobile apps.

```javascript
import { MobileHealthCopilot } from './mobileClient';

const copilot = new MobileHealthCopilot({ baseUrl: 'http://10.0.2.2:8000' });

// Set token after login
copilot.setAuthToken(userJwtToken);

// Send message
const response = await copilot.sendChatMessage("What are the side effects of levothyroxine?", conversationId);
console.log(response.reply);
```

---

## 5. Mobile Security & CORS

The backend CORS middleware is pre-configured to support Capacitor webviews (`capacitor://localhost`), Ionic, and local mobile dev origins.
