import React from 'react';
import { User, Activity, Clock, Pill, ShieldAlert, FileText } from 'lucide-react';

export const PatientContextPanel = ({ patientContext }) => {
  if (!patientContext) {
    return (
      <div style={{ padding: '16px', color: '#64748B', fontSize: '0.8rem', textAlign: 'center' }}>
        No active patient context gathered for this session.
      </div>
    );
  }

  const { age, sex, symptoms, duration, medications, known_conditions, lab_results } = patientContext;

  const cardStyle = {
    background: '#FFFFFF',
    border: '1px solid #E2E8F0',
    borderRadius: '12px',
    padding: '10px 12px',
    marginBottom: '8px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
  };

  const labelStyle = {
    fontSize: '0.675rem',
    fontWeight: 800,
    color: '#0B5A54',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '4px'
  };

  const valueStyle = {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#0F172A'
  };

  const tagStyle = {
    display: 'inline-block',
    background: '#E3F3F1',
    border: '1px solid rgba(11, 90, 84, 0.2)',
    color: '#0B5A54',
    borderRadius: '9999px',
    padding: '2px 8px',
    fontSize: '0.725rem',
    fontWeight: 700
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', textAlign: 'left' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingBottom: '8px',
        borderBottom: '1px solid #E2E8F0',
        marginBottom: '6px'
      }}>
        <h4 style={{ color: '#0F172A', fontSize: '0.85rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={16} color="#0B5A54" />
          Patient Context Memory
        </h4>
        <span style={{ fontSize: '0.675rem', color: '#64748B', fontWeight: 600 }}>Active Session</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        {/* Demographics */}
        <div style={cardStyle}>
          <div style={labelStyle}><User size={12} color="#0B5A54" /> Demographics</div>
          <div style={valueStyle}>
            {age ? `${age} yrs` : 'Unspecified'} • {sex || 'Unspecified'}
          </div>
        </div>

        {/* Duration */}
        <div style={cardStyle}>
          <div style={labelStyle}><Clock size={12} color="#0B5A54" /> Duration</div>
          <div style={valueStyle}>{duration || 'Unspecified'}</div>
        </div>
      </div>

      {/* Symptoms */}
      <div style={cardStyle}>
        <div style={labelStyle}><Activity size={12} color="#0B5A54" /> Tracked Symptoms</div>
        {symptoms && symptoms.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
            {symptoms.map((s, idx) => (
              <span key={idx} style={tagStyle}>{s}</span>
            ))}
          </div>
        ) : (
          <div style={{ color: '#94A3B8', fontSize: '0.75rem' }}>None specified yet</div>
        )}
      </div>

      {/* Medications */}
      <div style={cardStyle}>
        <div style={labelStyle}><Pill size={12} color="#0B5A54" /> Current Medications</div>
        {medications && medications.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
            {medications.map((m, idx) => (
              <span key={idx} style={{ ...tagStyle, background: '#FEF3C7', color: '#92400E', borderColor: '#FDE68A' }}>
                {m}
              </span>
            ))}
          </div>
        ) : (
          <div style={{ color: '#94A3B8', fontSize: '0.75rem' }}>None reported</div>
        )}
      </div>

      {/* Known Conditions */}
      <div style={cardStyle}>
        <div style={labelStyle}><ShieldAlert size={12} color="#E11D48" /> Known Conditions</div>
        {known_conditions && known_conditions.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
            {known_conditions.map((c, idx) => (
              <span key={idx} style={{ ...tagStyle, background: '#FFE4E6', color: '#9F1239', borderColor: '#FECDD3' }}>
                {c}
              </span>
            ))}
          </div>
        ) : (
          <div style={{ color: '#94A3B8', fontSize: '0.75rem' }}>None reported</div>
        )}
      </div>

      {/* Lab Results */}
      {lab_results && Object.keys(lab_results).length > 0 && (
        <div style={cardStyle}>
          <div style={labelStyle}><FileText size={12} color="#0B5A54" /> Laboratory Values</div>
          <div style={{ marginTop: '4px', fontSize: '0.75rem' }}>
            {Object.entries(lab_results).map(([k, v], idx) => (
              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                <span style={{ fontWeight: 600, color: '#334155' }}>{k}:</span>
                <span style={{ color: '#0B5A54', fontWeight: 700 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
