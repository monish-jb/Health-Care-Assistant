import React from 'react';
import { AlertOctagon, PhoneCall } from 'lucide-react';

export const EmergencyBanner = ({ triageLevel }) => {
  if (triageLevel !== 'EMERGENCY' && triageLevel !== 'URGENT_EVALUATION') {
    return null;
  }

  const isEmergency = triageLevel === 'EMERGENCY';

  return (
    <div style={{
      background: isEmergency ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
      border: isEmergency ? '1px solid rgba(239, 68, 68, 0.5)' : '1px solid rgba(245, 158, 11, 0.5)',
      borderRadius: '12px',
      padding: '16px 20px',
      marginBottom: '16px',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '14px',
      boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
    }}>
      <div style={{
        background: isEmergency ? '#ef4444' : '#f59e0b',
        borderRadius: '50%',
        padding: '8px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        shrink: 0
      }}>
        <AlertOctagon size={22} color="#fff" />
      </div>

      <div style={{ flex: 1 }}>
        <h4 style={{
          color: isEmergency ? '#fca5a5' : '#fde68a',
          fontSize: '0.95rem',
          fontWeight: 700,
          margin: '0 0 4px 0'
        }}>
          {isEmergency ? 'CRITICAL MEDICAL EMERGENCY DETECTED' : 'URGENT MEDICAL EVALUATION ADVISED'}
        </h4>
        <p style={{
          color: '#f8fafc',
          fontSize: '0.85rem',
          lineHeight: 1.4,
          margin: 0
        }}>
          {isEmergency
            ? 'The symptoms provided may indicate a high-risk medical condition. Please call 911 or visit the nearest emergency department immediately.'
            : 'These symptoms warrant timely clinical evaluation. Please contact your doctor or an urgent care clinic within 24 hours.'}
        </p>
      </div>

      {isEmergency && (
        <a
          href="tel:911"
          className="btn-danger"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            textDecoration: 'none',
            whiteSpace: 'nowrap',
            padding: '8px 14px',
            fontSize: '0.85rem',
            fontWeight: 700
          }}
        >
          <PhoneCall size={16} /> Call 911
        </a>
      )}
    </div>
  );
};
