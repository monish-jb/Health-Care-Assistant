import httpx
import logging
import random
from typing import List, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)

HEALTH_SYSTEM_PROMPT = """You are Healthcare Knowledge Navigator, a modern conversational health companion inspired by August AI.
Your purpose is to assist users in understanding medical information, symptoms, laboratory reports, and treatment guidelines.

CRITICAL SAFETY & MEDICAL RESPONSIBILITY MANDATE:
1. You are a health information and navigation assistant. You are NOT a doctor.
2. DO NOT claim to diagnose diseases or conditions.
3. DO NOT prescribe medications or suggest modifying dosages.
4. Structure your response clearly using the following markdown headings when answering medical queries:
   ### Summary
   ### What the evidence suggests
   ### Possible explanations
   ### What information is missing
   ### Recommended next steps
   ### When to seek urgent care
5. Cite retrieved evidence naturally using numbered citations [1], [2] where applicable.
6. Clearly distinguish between user-provided information and retrieved medical evidence."""

SYSTEM_PROMPT = HEALTH_SYSTEM_PROMPT

def get_system_prompt(intent: str, has_context: bool) -> str:
    prompt = HEALTH_SYSTEM_PROMPT
    if has_context:
        prompt += "\n\nGROUNDING INSTRUCTIONS:\nBase your response strictly on the retrieved medical evidence context provided below. Cite all claims with [1], [2], etc."
    else:
        prompt += "\n\nGROUNDING INSTRUCTIONS:\nNo specific knowledge base context was retrieved. Provide general health information grounded in standard clinical guidance while stating clearly that specific documentation was unavailable."
    
    return prompt

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
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        intent: Optional[str] = None,
        is_escalated: bool = False,
        escalation_reason: Optional[str] = None
    ) -> str:
        user_msg = messages[-1]["content"] if messages else ""
        user_msg_lower = user_msg.lower().strip()

        if is_escalated:
            reason_text = f" ({escalation_reason})" if escalation_reason else ""
            return (
                f"🚨 **Safety Alert / Escalation Notice**\n\n"
                f"Your query has triggered a safety review{reason_text}. "
                f"Please consult a qualified healthcare provider or seek urgent medical attention."
            )
        
        # Healthcare Synthesis Template Response
        if context:
            return (
                f"Based on the medical evidence and guidelines retrieved:\n\n"
                f"### Summary\n"
                f"Thank you for sharing your health query. Based on your described symptoms and our knowledge base, here is an evidence-grounded overview [1].\n\n"
                f"### What the evidence suggests\n"
                f"{context}\n\n"
                f"### Possible explanations\n"
                f"• Potential underlying physiological or lifestyle factors [1].\n"
                f"• Acute vs chronic symptom presentation requiring clinical observation.\n\n"
                f"### What information is missing\n"
                f"Further context such as exact onset, accompanying signs, and personal medical history would help refine this overview.\n\n"
                f"### Recommended next steps\n"
                f"1. Track symptom frequency and intensity in a log.\n"
                f"2. Schedule a routine consultation with your primary care provider.\n\n"
                f"### When to seek urgent care\n"
                f"Seek immediate medical attention if you experience sudden worsening, high fever, chest discomfort, or severe difficulty breathing."
            )

        # Greetings
        if any(greet in user_msg_lower for greet in ["hello", "hi", "hey", "greetings", "good morning"]):
            return "Hello! I am your Healthcare Knowledge Navigator. How can I help you understand your symptoms, lab reports, or health questions today?"

        # Fallback template
        return (
            f"### Summary\n"
            f"I have noted your message: '{user_msg}'. As your healthcare companion, I am here to help navigate health information, symptoms, and clinical guidelines.\n\n"
            f"### Recommended Next Steps\n"
            f"Please share any additional details regarding how long you've experienced this, any accompanying symptoms, or relevant medical history so I can assist you effectively."
        )

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
            prompt_messages.append({"role": "system", "content": f"Retrieved Evidence Context:\n{context}"})
            
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
            sys_prompt += f"\n\nRetrieved Evidence Context:\n{context}"
            
        formatted_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] in ["user", "assistant"]]
        payload = {"model": "claude-3-5-sonnet-20240620", "max_tokens": 1024, "system": sys_prompt, "messages": formatted_messages}
        
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
            prompt_messages.append({"role": "system", "content": f"Retrieved Evidence Context:\n{context}"})
            
        for m in messages:
            if m["role"] in ["user", "assistant"]:
                prompt_messages.append({"role": m["role"], "content": m["content"]})
                
        payload = {"model": settings.OPENAI_MODEL, "messages": prompt_messages, "max_tokens": 1024}
        
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
            sys_prompt += f"\n\nRetrieved Evidence Context:\n{context}"
            
        gemini_contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages]
        payload = {
            "contents": gemini_contents,
            "systemInstruction": {"parts": [{"text": sys_prompt}]},
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3}
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
