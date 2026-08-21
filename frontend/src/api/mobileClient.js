/**
 * Mobile SDK Client for Health-Care-Assistant LLM RAG Service.
 * Reusable helper class for mobile apps (React Native, Capacitor, Ionic, WebViews).
 */

export class MobileHealthCopilot {
  constructor({ baseUrl = 'http://localhost:8000', token = null } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.token = token;
  }

  setAuthToken(token) {
    this.token = token;
  }

  getHeaders() {
    const headers = {
      'Content-Type': 'application/json'
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  /**
   * Handshake endpoint to check backend LLM provider & RAG status.
   */
  async getConfig() {
    const res = await fetch(`${this.baseUrl}/mobile/api/config`, {
      method: 'GET',
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error(`Config fetch failed: ${res.statusText}`);
    return res.json();
  }

  /**
   * Standalone rapid symptom triage check.
   */
  async checkTriage(symptomsText) {
    const res = await fetch(`${this.baseUrl}/mobile/api/triage`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ symptoms: symptomsText })
    });
    if (!res.ok) throw new Error(`Triage evaluation failed: ${res.statusText}`);
    return res.json();
  }

  /**
   * Send a chat prompt to the LLM RAG engine.
   */
  async sendChatMessage(content, conversationId = null) {
    const res = await fetch(`${this.baseUrl}/mobile/api/chat`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        conversation_id: conversationId,
        content: content
      })
    });
    if (!res.ok) throw new Error(`Mobile chat failed: ${res.statusText}`);
    return res.json();
  }
}
