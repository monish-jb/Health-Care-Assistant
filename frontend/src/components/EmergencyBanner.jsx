import React from 'react';
import { AlertOctagon, PhoneCall, ShieldAlert } from 'lucide-react';

export const EmergencyBanner = ({ triageLevel }) => {
  if (triageLevel !== 'EMERGENCY' && triageLevel !== 'URGENT_EVALUATION') {
    return (
      <div style={{
        padding: '10px 14px',
        borderRadius: '14px',
        background: '#E3F3F1',
        border: '1px solid rgba(11, 90, 84, 0.15)',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '16px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
      }}>
        <ShieldAlert size={18} color="#0B5A54" style={{ shrink: 0 }} />
        <div style={{ fontSize: '0.75rem', color: '#0B5A54', fontWeight: 600, lineHeight: 1.4 }}>
          <strong style={{ fontWeight: 800 }}>Medical Notice: </strong>
          Preliminary symptom guidance. For life-threatening emergencies, call 108 / 911 immediately.
        </div>
      </div>
    );
  }

  const isEmergency = triageLevel === 'EMERGENCY';

  return (
    <div style={{
      background: isEmergency ? '#FFE4E6' : '#FEF3C7',
      border: isEmergency ? '1px solid #FECDD3' : '1px solid #FDE68A',
      borderRadius: '16px',
      padding: '14px 16px',
      marginBottom: '16px',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '12px',
      boxShadow: '0 4px 12px rgba(225, 29, 72, 0.08)'
    }}>
      <div style={{
        background: isEmergency ? '#E11D48' : '#D97706',
        borderRadius: '50%',
        width: '32px',
        height: '32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        shrink: 0
      }}>
        <AlertOctagon size={18} color="#fff" />
      </div>

      <div style={{ flex: 1, textAlign: 'left' }}>
        <h4 style={{
          color: isEmergency ? '#9F1239' : '#92400E',
          fontSize: '0.875rem',
          fontWeight: 800,
          margin: '0 0 2px 0'
        }}>
          {isEmergency ? 'Critical Medical Emergency Detected' : 'Urgent Clinical Evaluation Advised'}
        </h4>
        <p style={{
          color: isEmergency ? '#881337' : '#78350F',
          fontSize: '0.775rem',
          lineHeight: 1.4,
          margin: 0,
          fontWeight: 500
        }}>
          {isEmergency
            ? 'Reported symptoms indicate a high-risk situation. Please call emergency services or visit the nearest ER immediately.'
            : 'These symptoms warrant timely evaluation. Please contact an urgent care clinic or your physician today.'}
        </p>
      </div>

      {isEmergency && (
        <a
          href="tel:911"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            textDecoration: 'none',
            whiteSpace: 'nowrap',
            padding: '8px 14px',
            fontSize: '0.8rem',
            fontWeight: 800,
            borderRadius: '9999px',
            background: '#E11D48',
            color: '#FFFFFF',
            boxShadow: '0 2px 8px rgba(225, 29, 72, 0.3)'
          }}
        >
          <PhoneCall size={14} /> Call 911
        </a>
      )}
    </div>
  );
};
