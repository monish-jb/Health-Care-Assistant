import React, { useState, useEffect, useRef } from 'react';
import client from '../api/client';
import { ReasoningBadge } from '../components/ReasoningBadge';
import { FeedbackButtons } from '../components/FeedbackButtons';
import { FollowUpChips } from '../components/FollowUpChips';
import { PatientContextPanel } from '../components/PatientContextPanel';
import { EmergencyBanner } from '../components/EmergencyBanner';
import { CitationModal } from '../components/CitationModal';
import { DoctorBookingCard } from '../components/DoctorBookingCard';
import {
  Send,
  Sparkles,
  RefreshCw,
  Heart,
  Activity,
  Paperclip,
  ChevronRight,
  User,
  Plus
} from 'lucide-react';

export const ChatPage = () => {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [patientContext, setPatientContext] = useState(null);
  const [triageAssessment, setTriageAssessment] = useState(null);
  const [inputContent, setInputContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [showContextPanel, setShowContextPanel] = useState(false);
  const [showSessionDrawer, setShowSessionDrawer] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [bottomTab, setBottomTab] = useState('health-ai');

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const chatInputRef = useRef(null);

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
      setTriageAssessment(null);
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
    setTriageAssessment(null);
    setInputContent('');
    setShowSessionDrawer(false);
  };

  const executeSendMessage = async (userText) => {
    if (!userText.trim() || sending) return;

    setInputContent('');
    setSending(true);

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

      const { conversation_id, bot_message, patient_context: updatedCtx, triage_assessment: triageInfo } = res.data;
      setPatientContext(updatedCtx);
      if (triageInfo) {
        setTriageAssessment(triageInfo);
      }

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
    if (chipText.toLowerCase() === 'other' || chipText.toLowerCase() === 'others') {
      const customResponse = prompt("Please enter your custom response:");
      if (customResponse && customResponse.trim()) {
        executeSendMessage(customResponse.trim());
      }
    } else {
      executeSendMessage(chipText);
    }
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
      alert(`Document uploaded: ${res.data.filename}`);
      executeSendMessage(`I have uploaded my medical report "${file.name}". Please summarize key clinical findings.`);
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed. Please ensure backend is running.");
    } finally {
      setUploadingDoc(false);
    }
  };

  const currentTriageLevel = messages.length > 0
    ? messages[messages.length - 1].triage_level || 'GENERAL_INFO'
    : 'GENERAL_INFO';

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0F172A',
      display: 'flex',
      justifyContent: 'center',
      padding: '0',
      width: '100%'
    }}>
      {/* MOBILE APPLICATION SHELL CONTAINER */}
      <div style={{
        maxWidth: '520px',
        width: '100%',
        minHeight: '100vh',
        background: '#FFFFFF',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.4)',
        borderLeft: '1px solid rgba(255,255,255,0.05)',
        borderRight: '1px solid rgba(255,255,255,0.05)'
      }}>

        {/* TOP MOBILE APP BAR */}
        <div style={{
          background: '#FFFFFF',
          borderBottom: '1px solid #E2E8F0',
          padding: '12px 16px',
          position: 'sticky',
          top: 0,
          zIndex: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #0B5A54 0%, #14B8A6 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Heart size={18} color="#FFFFFF" fill="#FFFFFF" />
              </div>
              <h1 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0F172A', margin: 0, letterSpacing: '-0.02em' }}>
                Health AI
              </h1>
            </div>
            <p style={{ fontSize: '0.675rem', color: '#64748B', margin: '2px 0 0 40px', fontWeight: 600 }}>
              Clinical Assistant & Multi-Agent Guidance
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{
              fontSize: '0.675rem',
              fontWeight: 800,
              color: '#0B5A54',
              background: '#E3F3F1',
              padding: '4px 10px',
              borderRadius: '9999px',
              border: '1px solid rgba(11, 90, 84, 0.2)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981' }} />
              AI Active
            </span>

            <button
              onClick={handleStartNewChat}
              title="New Health Chat"
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                background: '#F8FAFC',
                border: '1px solid #E2E8F0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: '#0F172A'
              }}
            >
              <RefreshCw size={15} />
            </button>

            <button
              onClick={() => setShowContextPanel(!showContextPanel)}
              title="Patient Context Memory"
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                background: showContextPanel ? '#E3F3F1' : '#F8FAFC',
                border: showContextPanel ? '1px solid #0B5A54' : '1px solid #E2E8F0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: showContextPanel ? '#0B5A54' : '#0F172A'
              }}
            >
              <Activity size={15} />
            </button>
          </div>
        </div>

        {/* PATIENT CONTEXT DRAWER / PANEL (MOBILE TOGGLE) */}
        {showContextPanel && (
          <div style={{
            background: '#F8FAFC',
            borderBottom: '2px solid #E2E8F0',
            padding: '14px',
            animation: 'fadeIn 0.2s ease-in-out'
          }}>
            <PatientContextPanel patientContext={patientContext} />
          </div>
        )}

        {/* CHAT MESSAGES STREAM AREA */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          paddingBottom: '110px',
          background: '#FAFAFA'
        }}>
          {/* Medical Disclaimer Banner */}
          <EmergencyBanner triageLevel={currentTriageLevel} />

          {messages.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '24px 8px',
              color: '#64748B'
            }}>
              <div style={{
                width: '56px',
                height: '56px',
                borderRadius: '20px',
                background: '#E3F3F1',
                border: '1px solid rgba(11, 90, 84, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '12px'
              }}>
                <Sparkles size={28} color="#0B5A54" />
              </div>
              <h3 style={{ color: '#0F172A', fontWeight: 800, fontSize: '1.15rem', marginBottom: '6px' }}>
                Healthcare Knowledge Copilot
              </h3>
              <p style={{ fontSize: '0.825rem', color: '#64748B', maxWidth: '340px', lineHeight: 1.5, marginBottom: '20px' }}>
                Describe any symptoms or upload lab reports. The 4-agent system provides preliminary triage, doctor booking, SOAP notes, and care reminders.
              </p>

              {/* Quick Prompt Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
                {[
                  "I have had fever and chills for 2 days.",
                  "I am feeling extreme fatigue and weight gain.",
                  "What does a high TSH level indicate?",
                  "I have sharp stomach pain and nausea."
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => executeSendMessage(prompt)}
                    style={{
                      background: '#FFFFFF',
                      border: '1px solid #E2E8F0',
                      borderRadius: '14px',
                      padding: '10px 14px',
                      textAlign: 'left',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      color: '#1E293B',
                      cursor: 'pointer',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <span>{prompt}</span>
                    <ChevronRight size={14} color="#94A3B8" />
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
                    alignItems: isUser ? 'flex-end' : 'flex-start'
                  }}
                >
                  <div style={{
                    maxWidth: '88%',
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    gap: '8px',
                    alignItems: 'flex-start'
                  }}>
                    {/* Avatar Icon */}
                    <div style={{
                      width: '28px',
                      height: '28px',
                      borderRadius: '50%',
                      background: isUser ? '#0F172A' : '#0B5A54',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      shrink: 0,
                      color: '#FFFFFF',
                      marginTop: '2px'
                    }}>
                      {isUser ? <User size={14} /> : <Heart size={14} fill="#FFFFFF" />}
                    </div>

                    {/* Bubble Content */}
                    <div style={{ width: '100%' }}>
                      <div
                        style={{
                          background: isUser ? 'linear-gradient(135deg, #0B5A54 0%, #14B8A6 100%)' : '#FFFFFF',
                          border: isUser ? 'none' : '1px solid #E2E8F0',
                          borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                          padding: '12px 16px',
                          color: isUser ? '#FFFFFF' : '#0F172A',
                          fontSize: '0.85rem',
                          lineHeight: 1.55,
                          whiteSpace: 'pre-wrap',
                          boxShadow: isUser
                            ? '0 3px 10px rgba(11, 90, 84, 0.2)'
                            : '0 2px 6px rgba(0,0,0,0.04)',
                          textAlign: 'left'
                        }}
                      >
                        {msg.content}

                        {/* Follow-Up Quick Option Chips */}
                        {!isUser && msg.followup_options && (
                          <FollowUpChips
                            options={msg.followup_options}
                            onSelectOption={handleSelectOptionChip}
                            disabled={sending}
                          />
                        )}
                      </div>

                      {/* Evidence Reasoning & Citations — only on final assessment, not during conversational intake */}
                      {!isUser && msg.rag_grounded && msg.citations && (
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

          {/* Finalized Disease Triage & Recommended Doctor Booking Card */}
          {triageAssessment?.is_finalized && triageAssessment?.recommended_doctor && (
            <DoctorBookingCard
              triageData={triageAssessment}
              conversationId={activeConvId}
              onBookingSuccess={(appt) => {
                console.log("Appointment booked:", appt);
              }}
            />
          )}

          {sending && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: '#0B5A54',
              fontSize: '0.775rem',
              fontWeight: 700,
              padding: '6px 10px'
            }}>
              <RefreshCw size={14} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
              <span>AI Triage Agent is evaluating symptoms & clinical guidelines...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* CLEAN MOBILE INPUT BAR (STICKY AT BOTTOM) */}
        <div style={{
          position: 'sticky',
          bottom: 0,
          width: '100%',
          padding: '12px 16px',
          background: 'rgba(255, 255, 255, 0.98)',
          backdropFilter: 'blur(12px)',
          borderTop: '1px solid #E2E8F0',
          zIndex: 30
        }}>
          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
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
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: '#F1F5F9',
                border: '1px solid #E2E8F0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#64748B',
                cursor: 'pointer'
              }}
              title="Attach lab report (.pdf, .txt)"
            >
              <Paperclip size={16} />
            </button>

            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '9999px',
              padding: '4px 12px'
            }}>
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: '#E3F3F1',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#0B5A54'
              }}>
                <Sparkles size={12} />
              </div>
              <input
                type="text"
                ref={chatInputRef}
                value={inputContent}
                onChange={(e) => setInputContent(e.target.value)}
                placeholder="Describe your symptoms or reply to questions..."
                disabled={sending}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  fontSize: '0.825rem',
                  fontWeight: 600,
                  color: '#0F172A',
                  padding: '6px 0'
                }}
              />
            </div>

            <button
              type="submit"
              disabled={!inputContent.trim() || sending}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #0B5A54 0%, #14B8A6 100%)',
                border: 'none',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: inputContent.trim() && !sending ? 'pointer' : 'not-allowed',
                opacity: inputContent.trim() && !sending ? 1 : 0.4,
                boxShadow: '0 2px 8px rgba(11, 90, 84, 0.3)',
                transition: 'all 0.15s ease'
              }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>

      </div>

      {/* Citation Modal */}
      {selectedCitation && (
        <CitationModal
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </div>
  );
};
