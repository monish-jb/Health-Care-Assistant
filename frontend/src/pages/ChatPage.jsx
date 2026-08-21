import React, { useState, useEffect, useRef } from 'react';
import client from '../api/client';
import { ReasoningBadge } from '../components/ReasoningBadge';
import { FeedbackButtons } from '../components/FeedbackButtons';
import { FollowUpChips } from '../components/FollowUpChips';
import { PatientContextPanel } from '../components/PatientContextPanel';
import { EmergencyBanner } from '../components/EmergencyBanner';
import { CitationModal } from '../components/CitationModal';
import {
  Plus,
  Send,
  MessageSquare,
  Trash2,
  CheckCircle,
  AlertTriangle,
  Bot,
  User,
  Clock,
  Heart,
  Sparkles,
  RefreshCw,
  Activity,
  Paperclip,
  ShieldAlert,
  ChevronRight,
  BookOpen
} from 'lucide-react';

export const ChatPage = () => {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [patientContext, setPatientContext] = useState(null);
  const [inputContent, setInputContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [showContextPanel, setShowContextPanel] = useState(true);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Fetch conversation list
  const loadConversations = async (selectId = null) => {
    try {
      const res = await client.get('/chat/conversations');
      setConversations(res.data);
      if (selectId) {
        setActiveConvId(selectId);
      } else if (!activeConvId && res.data.length > 0) {
        setActiveConvId(res.data[0].id);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  // Fetch active conversation detail
  useEffect(() => {
    if (!activeConvId) {
      setActiveConv(null);
      setMessages([]);
      setPatientContext(null);
      return;
    }

    const fetchDetail = async () => {
      try {
        const res = await client.get(`/chat/conversations/${activeConvId}`);
        setActiveConv(res.data);
        setMessages(res.data.messages || []);
        setPatientContext(res.data.patient_context || null);
      } catch (err) {
        console.error("Failed to fetch conversation details:", err);
      }
    };

    fetchDetail();
  }, [activeConvId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleStartNewChat = () => {
    setActiveConvId(null);
    setActiveConv(null);
    setMessages([]);
    setPatientContext(null);
    setInputContent('');
  };

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this session?")) return;

    try {
      await client.delete(`/chat/conversations/${convId}`);
      if (activeConvId === convId) {
        setActiveConvId(null);
        setActiveConv(null);
        setMessages([]);
        setPatientContext(null);
      }
      loadConversations();
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const executeSendMessage = async (textToSend) => {
    if (!textToSend.trim() || sending) return;

    const userText = textToSend.trim();
    setInputContent('');
    setSending(true);

    // Optimistic user message preview
    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: userText,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await client.post('/chat/message', {
        conversation_id: activeConvId,
        content: userText
      });

      const { conversation_id, bot_message, patient_context: updatedCtx } = res.data;
      setPatientContext(updatedCtx);

      if (!activeConvId) {
        setActiveConvId(conversation_id);
        await loadConversations(conversation_id);
      } else {
        setMessages((prev) => {
          const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
          return [...filtered, res.data.user_message, bot_message];
        });
        const detailRes = await client.get(`/chat/conversations/${conversation_id}`);
        setActiveConv(detailRes.data);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      alert("Failed to send message. Please check backend connection.");
    } finally {
      setSending(false);
    }
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    executeSendMessage(inputContent);
  };

  const handleSelectOptionChip = (chipText) => {
    executeSendMessage(chipText);
  };

  const handleSelectSuggestedPrompt = (promptText) => {
    executeSendMessage(promptText);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingDoc(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', 'Clinical Reference');

    try {
      const res = await client.post('/kb/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert(`Successfully processed document: ${res.data.filename} (${res.data.chunk_count} chunks extracted)`);
      // Ask LLM to summarize uploaded doc in chat
      executeSendMessage(`I have uploaded a medical document named '${res.data.filename}'. Could you explain its key clinical points or laboratory values?`);
    } catch (err) {
      console.error("Failed to upload document:", err);
      alert("Document upload failed. Ensure it is a valid .txt, .md, or .pdf file.");
    } finally {
      setUploadingDoc(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleResolve = async () => {
    if (!activeConvId) return;
    try {
      await client.post(`/chat/resolve/${activeConvId}`);
      setActiveConv((prev) => prev ? { ...prev, status: 'resolved' } : null);
      loadConversations(activeConvId);
    } catch (err) {
      console.error("Failed to resolve conversation:", err);
    }
  };

  const getStatusBadge = (statusStr) => {
    switch (statusStr) {
      case 'resolved':
        return (
          <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle size={10} /> Completed
          </span>
        );
      case 'escalated':
        return (
          <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.3)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <AlertTriangle size={10} /> Triage Alert
          </span>
        );
      default:
        return (
          <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(6, 182, 212, 0.15)', color: '#38bdf8', border: '1px solid rgba(6, 182, 212, 0.3)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={10} /> Active Session
          </span>
        );
    }
  };

  const latestMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const currentTriageLevel = latestMessage?.triage_level || 'GENERAL_INFO';

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 61px)', overflow: 'hidden' }}>
      {/* SIDEBAR: Conversation Sessions */}
      <div style={{
        width: '300px',
        background: 'rgba(15, 23, 42, 0.95)',
        borderRight: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        flexDirection: 'column',
        shrink: 0
      }}>
        {/* New Session Button */}
        <div style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <button
            onClick={handleStartNewChat}
            className="btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
          >
            <Plus size={18} /> New Health Session
          </button>
        </div>

        {/* Sessions List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px' }}>
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              Loading sessions...
            </div>
          ) : conversations.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              No previous consultations. Start a new session above!
            </div>
          ) : (
            conversations.map((conv) => {
              const isSelected = conv.id === activeConvId;
              return (
                <div
                  key={conv.id}
                  onClick={() => setActiveConvId(conv.id)}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    marginBottom: '6px',
                    cursor: 'pointer',
                    background: isSelected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                    border: isSelected ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid transparent',
                    transition: 'all 0.15s'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.875rem', color: isSelected ? '#ffffff' : '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px' }}>
                      {conv.title || `Consultation #${conv.id}`}
                    </span>
                    <button
                      onClick={(e) => handleDeleteConversation(e, conv.id)}
                      style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px' }}
                      title="Delete chat"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
                    {getStatusBadge(conv.status)}
                    <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                      {new Date(conv.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* MAIN THREAD AREA */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'rgba(9, 13, 22, 0.5)' }}>
        {/* Top Action Bar */}
        <div style={{
          padding: '14px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(17, 24, 39, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Heart size={18} color="#10b981" />
              {activeConv ? activeConv.title : 'Healthcare Companion Consultation'}
            </h3>
            {activeConv && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                {getStatusBadge(activeConv.status)}
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Session ID: #{activeConv.id}</span>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => setShowContextPanel(!showContextPanel)}
              className="btn-secondary"
              style={{ fontSize: '0.8rem', borderColor: showContextPanel ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.1)' }}
            >
              <Activity size={15} color="#10b981" /> {showContextPanel ? 'Hide Patient Context' : 'Show Patient Context'}
            </button>

            {activeConv && activeConv.status !== 'resolved' && (
              <button
                onClick={handleResolve}
                className="btn-secondary"
                style={{ fontSize: '0.8rem', borderColor: 'rgba(16, 185, 129, 0.3)', color: '#34d399' }}
              >
                <CheckCircle size={15} /> Complete Session
              </button>
            )}
          </div>
        </div>

        {/* MESSAGES CONTAINER */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          <EmergencyBanner triageLevel={currentTriageLevel} />

          {messages.length === 0 ? (
            <div style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              color: '#64748b',
              padding: '20px'
            }}>
              <div style={{
                width: '68px',
                height: '68px',
                borderRadius: '24px',
                background: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px'
              }}>
                <Heart size={34} color="#34d399" fill="#34d399" />
              </div>
              <h3 style={{ color: '#f1f5f9', fontWeight: 800, fontSize: '1.25rem', marginBottom: '8px' }}>
                Healthcare Knowledge Navigator
              </h3>
              <p style={{ maxWidth: '480px', fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '24px' }}>
                Tell me what you are experiencing or upload a medical report. I will gather clinical context, ask targeted follow-up questions, and provide evidence-grounded insights.
              </p>

              {/* Starter Prompts */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', maxWidth: '580px', width: '100%' }}>
                {[
                  "My mother has been feeling tired for the last few weeks.",
                  "What does a high TSH value in a blood report mean?",
                  "Can I take ibuprofen with blood pressure medication?",
                  "I have sharp abdominal pain for 2 days."
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelectSuggestedPrompt(prompt)}
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '10px',
                      padding: '12px 14px',
                      textAlign: 'left',
                      color: '#cbd5e1',
                      fontSize: '0.825rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                      e.currentTarget.style.background = 'rgba(30, 41, 59, 0.9)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                      e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                    }}
                  >
                    <span>"{prompt}"</span>
                    <ChevronRight size={14} color="#10b981" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  className="animate-fade-in"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    marginBottom: '20px'
                  }}
                >
                  <div style={{
                    maxWidth: '82%',
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    gap: '12px',
                    alignItems: 'flex-start'
                  }}>
                    {/* Avatar Icon */}
                    <div style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: '50%',
                      background: isUser ? 'linear-gradient(135deg, #06b6d4, #0891b2)' : 'linear-gradient(135deg, #10b981, #059669)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      shrink: 0,
                      boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
                    }}>
                      {isUser ? <User size={16} color="#fff" /> : <Heart size={16} color="#fff" fill="#fff" />}
                    </div>

                    {/* Bubble Content */}
                    <div style={{ width: '100%' }}>
                      <div
                        className="chat-bubble"
                        style={{
                          background: isUser ? 'rgba(6, 182, 212, 0.2)' : 'rgba(30, 41, 59, 0.85)',
                          border: isUser ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: isUser ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                          padding: '14px 18px',
                          color: '#f8fafc',
                          fontSize: '0.925rem',
                          lineHeight: 1.6,
                          whiteSpace: 'pre-wrap',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                        }}
                      >
                        {msg.content}

                        {/* Quick Option Chips (Follow-up questions) */}
                        {!isUser && msg.followup_options && (
                          <FollowUpChips
                            options={msg.followup_options}
                            onSelectOption={handleSelectOptionChip}
                            disabled={sending}
                          />
                        )}
                      </div>

                      {/* Reasoning & Citations Widget */}
                      {!isUser && (
                        <>
                          <ReasoningBadge
                            message={msg}
                            onSelectCitation={(c) => setSelectedCitation(c)}
                          />
                          <FeedbackButtons messageId={msg.id} initialFeedback={msg.feedback} />
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {sending && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#34d399', fontSize: '0.85rem', marginTop: '12px' }}>
              <RefreshCw size={16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
              <span>Analyzing clinical intent, patient context & evidence guidelines...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* INPUT FORM AREA */}
        <div style={{
          padding: '16px 24px',
          background: 'rgba(17, 24, 39, 0.9)',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={handleFileUpload}
              accept=".txt,.md,.pdf"
            />
            <button
              type="button"
              disabled={uploadingDoc || sending}
              onClick={() => fileInputRef.current?.click()}
              className="btn-secondary"
              style={{ padding: '12px', borderRadius: '8px' }}
              title="Attach lab report or clinical document (.pdf, .txt)"
            >
              <Paperclip size={18} color="#34d399" />
            </button>

            <input
              type="text"
              className="glass-input"
              style={{ flex: 1, padding: '14px 18px', fontSize: '0.925rem' }}
              placeholder="Describe your health question, symptoms, or medication..."
              value={inputContent}
              onChange={(e) => setInputContent(e.target.value)}
              disabled={sending}
            />

            <button
              type="submit"
              disabled={sending || !inputContent.trim()}
              className="btn-primary"
              style={{ padding: '0 24px', height: '48px' }}
            >
              <Send size={18} /> Send
            </button>
          </form>
        </div>
      </div>

      {/* PATIENT CONTEXT RIGHT SIDE PANEL */}
      {showContextPanel && (
        <PatientContextPanel patientContext={patientContext} />
      )}

      {/* CITATION PASSAGE MODAL */}
      {selectedCitation && (
        <CitationModal
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </div>
  );
};
