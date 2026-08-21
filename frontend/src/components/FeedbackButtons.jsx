import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import client from '../api/client';

export const FeedbackButtons = ({ messageId, initialFeedback }) => {
  const [feedback, setFeedback] = useState(initialFeedback);
  const [submitting, setSubmitting] = useState(false);

  const handleFeedback = async (val) => {
    if (submitting) return;
    try {
      setSubmitting(true);
      const newFeedback = feedback === val ? null : val; // toggle if already clicked
      if (newFeedback === null) return;

      await client.post('/chat/feedback', {
        message_id: messageId,
        feedback: newFeedback
      });
      setFeedback(newFeedback);
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', marginTop: '6px' }}>
      <span style={{ fontSize: '0.7rem', color: '#64748b', marginRight: '4px' }}>Helpful?</span>
      <button
        onClick={() => handleFeedback(1)}
        disabled={submitting}
        title="Thumbs Up"
        style={{
          background: feedback === 1 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.04)',
          border: feedback === 1 ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
          color: feedback === 1 ? '#34d399' : '#94a3b8',
          padding: '4px 8px',
          borderRadius: '6px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          fontSize: '0.7rem',
          transition: 'all 0.15s'
        }}
      >
        <ThumbsUp size={12} />
      </button>

      <button
        onClick={() => handleFeedback(-1)}
        disabled={submitting}
        title="Thumbs Down"
        style={{
          background: feedback === -1 ? 'rgba(244, 63, 94, 0.2)' : 'rgba(255, 255, 255, 0.04)',
          border: feedback === -1 ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
          color: feedback === -1 ? '#fb7185' : '#94a3b8',
          padding: '4px 8px',
          borderRadius: '6px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          fontSize: '0.7rem',
          transition: 'all 0.15s'
        }}
      >
        <ThumbsDown size={12} />
      </button>
    </div>
  );
};
