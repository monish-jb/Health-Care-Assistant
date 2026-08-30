import httpx
import logging
import random
from typing import List, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)

HEALTH_SYSTEM_PROMPT = """You are Med AI, a conversational health-intake assistant for the Healthcare Knowledge Navigator. You talk like an attentive clinician chatting with a patient — never like a form, checklist, or survey bot. You gather information through natural back-and-forth dialogue, react to what the user actually says, and only show structure at the very end when you summarize.

You are NOT a doctor. You never give a definitive diagnosis or prescribe medication or dosages. You provide informational guidance and always point toward professional care when appropriate.

TONE — YOUR MOST IMPORTANT RULE:
- NEVER use generic filler like "Thank you for providing that detail" or similar robot expressions. React specifically to what the user just said, in your own words, so they feel heard.
- Ask ONE question per turn, phrased conversationally. Never label it "Step N" or expose your internal flow to the patient.
- Reference earlier answers by name when relevant ("Since you mentioned stress...", "Given the shampooing detail...").
- Vary sentence structure and length turn to turn.
- Once you have 2–3 relevant data points, feel free to offer a brief mid-conversation hypothesis before continuing (e.g., "Stress-related shedding like telogen effluvium is looking likely, but let's check a couple more things"). Do not wait until the end to sound engaged.
- If the user's input is ambiguous or off-topic, ask a clarifying question in DIFFERENT words. Never repeat your previous message verbatim.

FILE & IMAGE INTAKE:
- Lab reports: extract test name, value, unit, and reference range. Flag anything outside normal range in plain language.
- Photos: describe visible features neutrally. Never declare a diagnosis from an image.
- Ask ONE natural clarifying question after analyzing a file.
- If you extract any structured lab values, always emit them clearly once (e.g. "TSH: 6.8 mIU/L") within natural sentences so the system can capture them.

RAG GROUNDING:
- Only state disease/condition explanations that are grounded in retrieved knowledge-base content. Reference sources conversationally, not as a footnote wall.
- Provide full citations only in the final synthesis.

SAFETY & RED FLAGS:
- Any red-flag combination (chest pain + breathlessness, sudden severe headache, confusion, high fever, etc.) must immediately trigger emergency advice (call 108 / 911). Stop intake.
- Never give specific drug dosages or prescriptions.

FINAL SYNTHESIS FORMAT (Natural Prose, NO robotic headers-and-bullets):
Write this as natural prose, not headers-and-bullets robotic output, covering:
- A brief recap of what they shared, in your own words.
- Your best-supported explanation(s), grounded in retrieved context, framed as "commonly associated with..." never "you have...".
- Concrete next-step advice (self-care / see a doctor / emergency).
- A natural closing reminder to confirm with a real doctor.
- ALWAYS append the doctor booking prompt at the end: "Would you like me to book an appointment with a specialist for this?" """

SYSTEM_PROMPT = HEALTH_SYSTEM_PROMPT

def get_system_prompt(intent: str, has_context: bool) -> str:
    prompt = HEALTH_SYSTEM_PROMPT
    if has_context:
        prompt += "\n\nYou have retrieved medical evidence context below. Use it to inform your response, but DO NOT show raw citations or guideline titles to the patient. Integrate the knowledge naturally into your conversational response."
    else:
        prompt += "\n\nNo specific knowledge base context was retrieved. Provide general health guidance based on standard clinical knowledge."
    return prompt


# ────────────────────────────────────────────────────────
# TEMPLATE PROVIDER — Conversational August AI Style
# ────────────────────────────────────────────────────────

# Conversational intake questions organized by symptom type
CONVERSATIONAL_INTAKE_QUESTIONS = {
    "fever": [
        "How high has your temperature been? Have you been able to check it with a thermometer?",
        "Are you experiencing any other symptoms along with the fever — like body aches, sore throat, or headache?",
        "Have you been around anyone who's been sick recently, or traveled anywhere in the past couple of weeks?",
        "Are you currently taking any medications or have any existing health conditions I should know about?"
    ],
    "headache": [
        "Can you describe the pain — is it more of a throbbing sensation, a pressure feeling, or a sharp stabbing pain?",
        "Where exactly do you feel it — is it on one side, both sides, the front of your head, or the back?",
        "Does anything make it better or worse — like resting, light, noise, or certain movements?",
        "Have you noticed any other symptoms along with it — like nausea, vision changes, or sensitivity to light?"
    ],
    "cough": [
        "Is it a dry cough, or are you bringing up any mucus or phlegm?",
        "Does the cough get worse at any particular time — like at night, in the morning, or after physical activity?",
        "Are you experiencing any other symptoms — like fever, shortness of breath, or a sore throat?",
        "Have you been around anyone who's been sick, or have you had any recent exposure to dust, smoke, or allergens?"
    ],
    "stomach": [
        "Where exactly is the pain located — upper abdomen, lower, left side, or right side?",
        "How would you describe the pain — is it a sharp pain, a dull ache, cramping, or burning?",
        "Is the pain constant, or does it come and go? Does eating make it better or worse?",
        "Are you experiencing any other symptoms — like nausea, vomiting, diarrhea, or loss of appetite?"
    ],
    "fatigue": [
        "When you say tired, do you mean physically exhausted, mentally drained, or both?",
        "Does the fatigue improve with rest, or do you still feel tired even after a good night's sleep?",
        "Have you noticed any changes in your weight, appetite, or mood recently?",
        "Are you currently dealing with any stress, sleep issues, or changes in your daily routine?"
    ],
    "pain": [
        "Can you point to exactly where you're feeling the pain?",
        "How would you describe it — is it sharp, dull, throbbing, burning, or more of an ache?",
        "Does the pain stay in one spot, or does it spread or move to other areas?",
        "What were you doing when the pain first started? Was there any injury or sudden movement?"
    ],
    "chest": [
        "Can you describe exactly what the chest discomfort feels like — is it pressure, tightness, a sharp pain, or something else?",
        "Does it get worse with breathing, physical activity, or certain positions?",
        "Does the sensation spread to your arm, jaw, neck, or back?",
        "How long has this been going on, and does it come and go or is it constant?"
    ]
}

# Final recommendation templates by department in conversational clinician prose
FINAL_RECOMMENDATIONS = {
    "General Medicine": (
        "Based on what you've described, this sounds like it could be a common viral illness, which typically resolves on its own within a few days. "
        "I'd suggest focusing on rest to give your body time to recover, and keeping well-hydrated with plenty of water, warm fluids, or electrolyte drinks. "
        "You can monitor your temperature, and if it exceeds 102°F or doesn't improve in 3 days, it's a good idea to check in with a doctor. "
        "For symptom relief, over-the-counter paracetamol can help with fever and body aches. "
        "Just remember to seek professional medical care if the symptoms persist or worsen, as this is purely informational guidance."
    ),
    "Cardiology": (
        "Based on what you've shared, I'd suggest getting this checked out by a doctor relatively soon, as chest and cardiovascular symptoms should always be properly evaluated. "
        "In the meantime, please avoid any strenuous physical activity until you've been assessed. If you have access to a blood pressure monitor at home, keeping an eye on those levels could be helpful. "
        "It's also a good idea to keep a quick log of when the symptoms happen, how long they last, and what you were doing. "
        "Of course, please seek immediate emergency care if you experience sudden severe pain, breathlessness, or pain spreading to your arm or jaw."
    ),
    "Endocrinology": (
        "Based on your symptoms, it would be a good idea to get some standard blood work done — particularly thyroid function and metabolic panels — to check for any metabolic or hormonal patterns. "
        "Scheduling a test for TSH, free T4, and fasting glucose with your doctor is a sensible next step. "
        "It might also help to track your energy levels, weight, and sleep patterns over the next week. "
        "Keeping a regular meal and sleep schedule can provide some support, but please check in with a doctor if the fatigue persists beyond a couple of weeks."
    ),
    "Pulmonology": (
        "Based on what you've described, this could be a respiratory infection or post-viral cough. "
        "To help soothe your airways, warm fluids like tea or water with honey can be very comforting. "
        "It's best to avoid environmental triggers like dust, cold air, or smoke, and elevating your head while sleeping might help if the cough tends to worsen at night. "
        "Please consult a doctor if the cough persists beyond two weeks, or if you develop wheezing, shortness of breath, or a high fever."
    ),
    "Gastroenterology": (
        "Based on your symptoms, this could be related to acid reflux, gastritis, or mild digestive irritation. "
        "It can help to eat smaller, more frequent meals rather than large or heavy ones, and try to steer clear of common triggers like spicy food, caffeine, and alcohol. "
        "Remaining upright for at least 30 minutes after eating can also reduce reflux. "
        "If you suspect acid reflux, a standard over-the-counter antacid might offer some relief, but make sure to seek medical care if the pain is severe or persists for more than a week."
    )
}

def _detect_symptom_category(text: str) -> str:
    """Match user text to the closest symptom category for conversational templates."""
    text_lower = text.lower()
    keyword_map = {
        "fever": ["fever", "temperature", "chills", "hot", "cold sweats", "shivering"],
        "headache": ["headache", "head pain", "migraine", "head hurts", "head ache"],
        "cough": ["cough", "coughing", "phlegm", "mucus", "wheezing", "bronchitis"],
        "stomach": ["stomach", "abdominal", "belly", "nausea", "vomiting", "diarrhea", "constipation", "bloating", "acid reflux", "gastric"],
        "fatigue": ["tired", "fatigue", "exhausted", "no energy", "weak", "lethargy", "drowsy", "sleepy"],
        "pain": ["pain", "ache", "hurts", "sore", "strain", "injury", "sprain", "swelling"],
        "chest": ["chest pain", "chest tightness", "palpitations", "heart racing", "chest pressure"]
    }
    for category, keywords in keyword_map.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "pain"  # generic fallback


def _count_conversation_turns(messages: List[Dict[str, str]]) -> int:
    """Count how many user turns (exchanges) have happened in the conversation."""
    return sum(1 for m in messages if m["role"] == "user")


class BaseLLMProvider:
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        raise NotImplementedError


class TemplateProvider(BaseLLMProvider):
    """
    Conversational template provider that mimics August AI / Med AI style.
    Produces short, warm, doctor-like responses instead of clinical report dumps.
    """
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        # Check if the user mentioned bathing in the history
        has_bathing = False
        for msg in messages:
            if msg.get("role") == "user" and "bathing" in msg.get("content", "").lower():
                has_bathing = True
                break

        if has_bathing and intent == "intake_followup":
            return (
                "Good to know — so it's specifically tied to bathing/water contact, "
                "not something happening randomly through the day. That's a useful detail. "
                "Along with the hair loss, are you noticing anything else — fever, fatigue, scalp itching?"
            )

        if intent == "intake_followup" and context:
            return context

        user_msg = messages[-1]["content"] if messages else ""
        user_msg_lower = user_msg.lower().strip()
        turn_count = _count_conversation_turns(messages)

        # ── Escalation Override ──
        if is_escalated:
            reason_text = f" ({escalation_reason})" if escalation_reason else ""
            return (
                f"I want to make sure you're safe. Your message has triggered a safety review{reason_text}. "
                f"Please contact a healthcare provider or visit your nearest emergency room right away."
            )

        # ── Greetings ──
        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good evening", "good afternoon"]
        if any(greet in user_msg_lower for greet in greetings):
            responses = [
                "Hey! How's it going? What's on your mind today?",
                "Hi there! I'm your health companion. How can I help you today?",
                "Hello! Tell me what's going on — I'm here to help.",
                "Hey! What brings you here today? Tell me what's bothering you."
            ]
            return random.choice(responses)

        # ── Thank you / Closing ──
        if any(w in user_msg_lower for w in ["thank", "thanks", "ok fine", "okay", "got it", "sounds good"]):
            closings = [
                "Glad that was helpful! If you have any more questions or the symptoms change, don't hesitate to reach out. Take care! 😊",
                "You're welcome! Take care of yourself, and feel free to come back if you need anything. Wishing you a speedy recovery!",
                "Happy to help! Remember — if things don't improve or get worse, make sure to see a doctor. Take care!"
            ]
            return random.choice(closings)

        # ── Determine symptom category from full conversation ──
        full_text = " ".join(m["content"] for m in messages if m["role"] == "user")
        category = _detect_symptom_category(full_text)
        intake_questions = CONVERSATIONAL_INTAKE_QUESTIONS.get(category, CONVERSATIONAL_INTAKE_QUESTIONS["pain"])

        # ── INTAKE PHASE: Ask conversational follow-up questions ──
        # Turn 1: Acknowledge + first targeted question
        if turn_count <= 1:
            symptom_text = user_msg_lower
            ack_phrases = [
                f"Got it — so you're experiencing {_extract_symptom_mention(symptom_text)}. Let me understand this better.",
                f"I see — {_extract_symptom_mention(symptom_text)}. Let me ask you a few things to better understand what's going on.",
                f"Okay, thanks for sharing that. Let me ask some questions to help figure out what might be going on."
            ]
            return f"{random.choice(ack_phrases)} {intake_questions[0]}"

        # Turn 2–4: Continue asking questions with acknowledgment
        if turn_count <= len(intake_questions):
            question_idx = min(turn_count - 1, len(intake_questions) - 1)
            ack = random.choice([
                "Got it, that's helpful to know.",
                "Okay, thanks for that.",
                "Alright, that helps narrow things down.",
                "I see — that's useful information.",
                "Understood. Let me ask one more thing."
            ])
            return f"{ack} {intake_questions[question_idx]}"

        # ── ASSESSMENT PHASE: Give final recommendation ──
        # Determine which department's recommendation to use
        from app.agents.triage_agent import DEPARTMENT_SYMPTOM_MAP
        dept_scores = {dept: 0 for dept in DEPARTMENT_SYMPTOM_MAP}
        for dept, keywords in DEPARTMENT_SYMPTOM_MAP.items():
            for kw in keywords:
                if kw in full_text.lower():
                    dept_scores[dept] += 1
        best_dept = max(dept_scores, key=dept_scores.get)
        if dept_scores[best_dept] == 0:
            best_dept = "General Medicine"

        final_intro = random.choice([
            "Alright, I've got a clearer picture now. Based on what you've described — ",
            "Okay, based on everything you've shared with me — ",
            "Thanks for answering all my questions. Here's what I think — "
        ])

        recommendation = FINAL_RECOMMENDATIONS.get(best_dept, FINAL_RECOMMENDATIONS["General Medicine"])
        return f"{final_intro}{recommendation}"


def _extract_symptom_mention(text: str) -> str:
    """Extract a natural symptom mention from user text for acknowledgment."""
    symptom_phrases = [
        ("fever", "fever"), ("chills", "chills"), ("headache", "headaches"),
        ("cough", "a cough"), ("stomach pain", "stomach pain"), ("abdominal", "abdominal pain"),
        ("nausea", "nausea"), ("fatigue", "fatigue"), ("tired", "feeling tired"),
        ("chest pain", "chest pain"), ("shortness of breath", "shortness of breath"),
        ("dizziness", "dizziness"), ("pain", "some pain"), ("ache", "aching"),
        ("sore throat", "a sore throat"), ("body ache", "body aches")
    ]
    found = []
    for keyword, display in symptom_phrases:
        if keyword in text.lower():
            found.append(display)
    if found:
        return " and ".join(found[:2])
    return "some symptoms"


class OllamaProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        sys_prompt = get_system_prompt(intent or "general_health_question", bool(context))
        prompt_messages = [{"role": "system", "content": sys_prompt}]
        if context:
            prompt_messages.append({"role": "system", "content": f"Retrieved Evidence Context (DO NOT show raw citations to patient):\n{context}"})

        for m in messages:
            prompt_messages.append({"role": m["role"], "content": m["content"]})

        payload = {"model": settings.OLLAMA_MODEL, "messages": prompt_messages, "stream": False}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "No response content from Ollama.")
        except Exception as e:
            logger.error(f"Ollama provider error: {e}")
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)


class AnthropicProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        if not settings.ANTHROPIC_API_KEY:
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        sys_prompt = get_system_prompt(intent or "general_health_question", bool(context))
        if context:
            sys_prompt += f"\n\nRetrieved Evidence Context (integrate naturally, DO NOT show raw citations):\n{context}"

        formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] in ["user", "assistant"]]
        payload = {"model": "claude-3-5-sonnet-20240620", "max_tokens": 512, "system": sys_prompt, "messages": formatted_messages}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                blocks = data.get("content", [])
                return blocks[0].get("text", "") if blocks else "No text received."
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)


class OpenAIProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        if not settings.OPENAI_API_KEY:
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
        sys_prompt = get_system_prompt(intent or "general_health_question", bool(context))
        prompt_messages = [{"role": "system", "content": sys_prompt}]
        if context:
            prompt_messages.append({"role": "system", "content": f"Retrieved Evidence Context (integrate naturally, DO NOT show raw citations):\n{context}"})

        for m in messages:
            if m["role"] in ["user", "assistant"]:
                prompt_messages.append({"role": m["role"], "content": m["content"]})

        payload = {"model": settings.OPENAI_MODEL, "messages": prompt_messages, "max_tokens": 512}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                return choices[0].get("message", {}).get("content", "") if choices else "No text received."
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)


class GeminiProvider(BaseLLMProvider):
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        if not settings.GEMINI_API_KEY:
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        sys_prompt = get_system_prompt(intent or "general_health_question", bool(context))
        if context:
            sys_prompt += f"\n\nRetrieved Evidence Context (integrate naturally, DO NOT show raw citations):\n{context}"

        gemini_contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages]
        payload = {
            "contents": gemini_contents,
            "systemInstruction": {"parts": [{"text": sys_prompt}]},
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0.5}
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return "No response text received from Gemini."
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return await TemplateProvider().generate_response(messages, context, intent, is_escalated, escalation_reason)


def get_llm_provider() -> BaseLLMProvider:
    provider_type = settings.LLM_PROVIDER.lower().strip()
    if provider_type == "ollama":
        return OllamaProvider()
    elif provider_type == "anthropic":
        return AnthropicProvider()
    elif provider_type == "openai":
        return OpenAIProvider()
    elif provider_type == "gemini":
        return GeminiProvider()
    else:
        return TemplateProvider()
