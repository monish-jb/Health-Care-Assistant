import React from 'react';
import { Zap, Database, ShieldCheck, BookOpen, Sparkles } from 'lucide-react';

export const ReasoningBadge = ({ message, onSelectCitation }) => {
  if (!message || message.role !== 'assistant') return null;

  const {
    intent = 'general_health_question',
    intent_confidence = 0,
    rag_grounded = false,
    retrieval_score = null,
    confidence_level = null,
    citations = null,
    response_time_ms = 0
  } = message;

  const confLevelStr = confidence_level || (rag_grounded ? 'MEDIUM' : 'LOW');
  
  const getConfStyle = (lvl) => {
    switch (lvl) {
      case 'HIGH':
        return { bg: '#D1FAE5', color: '#065F46', border: '#A7F3D0' };
      case 'MEDIUM':
        return { bg: '#FEF3C7', color: '#92400E', border: '#FDE68A' };
      default:
        return { bg: '#F1F5F9', color: '#475569', border: '#E2E8F0' };
    }
  };

  const confStyle = getConfStyle(confLevelStr);

  return (
    <div style={{
      marginTop: '8px',
      marginBottom: '4px',
      padding: '8px 12px',
      background: '#F8FAFC',
      borderRadius: '12px',
      border: '1px solid #E2E8F0',
      fontSize: '0.725rem',
      textAlign: 'left'
    }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          fontWeight: 800,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#0B5A54',
          fontSize: '0.65rem'
        }}>
          <ShieldCheck size={13} color="#0B5A54" /> Evidence Reasoning
        </span>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: '3px',
          color: '#64748B',
          fontFamily: 'monospace',
          fontSize: '0.65rem',
          fontWeight: 600
        }}>
          <Zap size={11} color="#D97706" /> {response_time_ms}ms
        </span>
      </div>

      {/* Badges Grid */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
        {/* Evidence Confidence Level */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '2px 8px',
          borderRadius: '9999px',
          background: confStyle.bg,
          color: confStyle.color,
          border: `1px solid ${confStyle.border}`,
          fontWeight: 800
        }}>
          <span>Confidence: {confLevelStr}</span>
        </div>

        {/* Intent Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '2px 8px',
          borderRadius: '9999px',
          background: '#E3F3F1',
          color: '#0B5A54',
          border: '1px solid rgba(11, 90, 84, 0.2)',
          fontWeight: 700
        }}>
          <span>Intent: {intent.replace('_', ' ')}</span>
        </div>

        {/* RAG Grounded Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: '9999px',
          background: rag_grounded ? '#E3F3F1' : '#F1F5F9',
          color: rag_grounded ? '#0B5A54' : '#64748B',
          border: '1px solid #E2E8F0',
          fontWeight: 600
        }}>
          <Database size={11} />
          <span>{rag_grounded ? 'Clinical RAG Grounded' : 'General Knowledge'}</span>
        </div>
      </div>

      {/* Citations */}
      {citations && citations.length > 0 && (
        <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid #E2E8F0' }}>
          <span style={{ fontSize: '0.65rem', color: '#64748B', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
            Retrieved Clinical Citations ({citations.length}):
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {citations.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelectCitation && onSelectCitation(c)}
                style={{
                  background: '#FFFFFF',
                  border: '1px solid #CBD5E1',
                  color: '#0B5A54',
                  borderRadius: '6px',
                  padding: '2px 6px',
                  fontSize: '0.675rem',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px',
                  fontWeight: 600
                }}
              >
                <BookOpen size={10} /> [{c.id}] {c.title}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
