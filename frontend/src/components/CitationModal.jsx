import React from 'react';
import { X, BookOpen, FileText, Calendar, Tag } from 'lucide-react';

export const CitationModal = ({ citation, onClose }) => {
  if (!citation) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        background: '#0f172a',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '560px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(30, 41, 59, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BookOpen size={20} color="#10b981" />
            <h3 style={{ color: '#f8fafc', fontSize: '1rem', fontWeight: 700, margin: 0 }}>
              Retrieved Evidence Source [{citation.id}]
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '20px' }}>
          <h4 style={{ color: '#38bdf8', fontSize: '1.05rem', fontWeight: 600, marginTop: 0, marginBottom: '12px' }}>
            {citation.title}
          </h4>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px', fontSize: '0.8rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '4px 10px', borderRadius: '12px' }}>
              <Tag size={12} /> {citation.source_type}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', padding: '4px 10px', borderRadius: '12px' }}>
              <FileText size={12} /> Section: {citation.section || 'General'}
            </span>
            {citation.year && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', padding: '4px 10px', borderRadius: '12px' }}>
                <Calendar size={12} /> {citation.year}
              </span>
            )}
          </div>

          <div style={{
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '10px',
            padding: '14px 16px',
            color: '#e2e8f0',
            fontSize: '0.875rem',
            lineHeight: 1.6,
            maxHeight: '240px',
            overflowY: 'auto',
            fontStyle: 'italic'
          }}>
            "{citation.passage}"
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          background: 'rgba(15, 23, 42, 0.9)',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          textAlign: 'right'
        }}>
          <button onClick={onClose} className="btn-secondary" style={{ padding: '6px 16px', fontSize: '0.825rem' }}>
            Close Source
          </button>
        </div>
      </div>
    </div>
  );
};
