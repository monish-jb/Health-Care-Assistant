import React from 'react';
import { Cpu, Zap, Database, AlertTriangle, ShieldCheck, BookOpen } from 'lucide-react';

export const ReasoningBadge = ({ message, onSelectCitation }) => {
  if (!message || message.role !== 'assistant') return null;

  const {
    intent = 'general_health_question',
    intent_confidence = 0,
    rag_grounded = false,
    retrieval_score = null,
    confidence_level = null,
    confidence_details = null,
    citations = null,
    triage_level = 'GENERAL_INFO',
    response_time_ms = 0
  } = message;

  const confLevelStr = confidence_level || (rag_grounded ? 'MEDIUM' : 'LOW');
  
  const getConfStyle = (lvl) => {
    switch (lvl) {
      case 'HIGH':
        return { bg: 'rgba(16, 185, 129, 0.18)', color: '#34d399', border: 'rgba(16, 185, 129, 0.4)' };
      case 'MEDIUM':
        return { bg: 'rgba(245, 158, 11, 0.18)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.4)' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', border: 'rgba(148, 163, 184, 0.3)' };
    }
  };

  const confStyle = getConfStyle(confLevelStr);

  return (
    <div style={{
      marginTop: '10px',
      marginBottom: '6px',
      padding: '10px 14px',
      background: 'rgba(15, 23, 42, 0.8)',
      borderRadius: '10px',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      fontSize: '0.75rem'
    }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: '#94a3b8',
          fontSize: '0.7rem'
        }}>
          <ShieldCheck size={14} color="#10b981" /> Evidence Reasoning & Confidence
        </span>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          color: '#64748b',
          fontFamily: 'monospace',
          fontSize: '0.7rem'
        }}>
          <Zap size={12} color="#f59e0b" /> {response_time_ms}ms
        </span>
      </div>

      {/* Badges Grid */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
        {/* Evidence Confidence Level */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 10px',
          borderRadius: '6px',
          background: confStyle.bg,
          color: confStyle.color,
          border: `1px solid ${confStyle.border}`,
          fontWeight: 700
        }}>
          <span>Evidence Confidence: <strong>{confLevelStr}</strong></span>
        </div>

        {/* Intent Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 8px',
          borderRadius: '6px',
          background: 'rgba(6, 182, 212, 0.15)',
          color: '#38bdf8',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          fontWeight: 600
        }}>
          <span>Intent: <strong>{intent.replace('_', ' ')}</strong></span>
        </div>

        {/* RAG Grounded Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '3px 8px',
          borderRadius: '6px',
          background: rag_grounded ? 'rgba(16, 185, 129, 0.12)' : 'rgba(255, 255, 255, 0.05)',
          color: rag_grounded ? '#34d399' : '#94a3b8',
          border: rag_grounded ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(255, 255, 255, 0.08)',
          fontWeight: 600
        }}>
          <Database size={12} />
          <span>{rag_grounded ? 'Clinical RAG Grounded' : 'General Knowledge'}</span>
        </div>
      </div>

      {/* Citations List Button Chips */}
      {citations && citations.length > 0 && (
        <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
          <span style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
            Retrieved Sources ({citations.length}):
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {citations.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelectCitation && onSelectCitation(c)}
                style={{
                  background: 'rgba(30, 41, 59, 0.9)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: '#38bdf8',
                  borderRadius: '6px',
                  padding: '3px 8px',
                  fontSize: '0.725rem',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
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
