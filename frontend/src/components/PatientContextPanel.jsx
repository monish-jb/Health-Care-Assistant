import React from 'react';
import { User, Activity, Clock, Pill, ShieldAlert, FileText, ChevronRight } from 'lucide-react';

export const PatientContextPanel = ({ patientContext }) => {
  if (!patientContext) {
    return (
      <div style={{ padding: '20px', color: '#64748b', fontSize: '0.85rem', textAlign: 'center' }}>
        No active patient context gathered for this session.
      </div>
    );
  }

  const { age, sex, symptoms, duration, medications, known_conditions, lab_results } = patientContext;

  return (
    <div style={{
      width: '300px',
      background: 'rgba(15, 23, 42, 0.95)',
      borderLeft: '1px solid rgba(255, 255, 255, 0.08)',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflowY: 'auto',
      padding: '16px'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        paddingBottom: '12px',
        marginBottom: '16px'
      }}>
        <Activity size={18} color="#10b981" />
        <h4 style={{ color: '#f8fafc', fontSize: '0.95rem', fontWeight: 700, margin: 0 }}>
          Patient Context Memory
        </h4>
      </div>

      {/* Demographics */}
      <div className="ctx-card">
        <div className="ctx-label"><User size={14} color="#06b6d4" /> Demographics</div>
        <div className="ctx-value">
          {age ? `${age} years old` : 'Age: Unspecified'} • {sex || 'Sex: Unspecified'}
        </div>
      </div>

      {/* Symptoms */}
      <div className="ctx-card">
        <div className="ctx-label"><Activity size={14} color="#f59e0b" /> Tracked Symptoms</div>
        {symptoms && symptoms.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '6px' }}>
            {symptoms.map((s, idx) => (
              <span key={idx} className="ctx-tag">{s}</span>
            ))}
          </div>
        ) : (
          <div className="ctx-value-muted">None specified yet</div>
        )}
      </div>

      {/* Duration */}
      <div className="ctx-card">
        <div className="ctx-label"><Clock size={14} color="#818cf8" /> Duration</div>
        <div className="ctx-value">{duration || 'Unspecified'}</div>
      </div>

      {/* Medications */}
      <div className="ctx-card">
        <div className="ctx-label"><Pill size={14} color="#ec4899" /> Current Medications</div>
        {medications && medications.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '6px' }}>
            {medications.map((m, idx) => (
              <span key={idx} className="ctx-tag-purple">{m}</span>
            ))}
          </div>
        ) : (
          <div className="ctx-value-muted">None reported</div>
        )}
      </div>

      {/* Known Conditions */}
      <div className="ctx-card">
        <div className="ctx-label"><ShieldAlert size={14} color="#ef4444" /> Known Conditions</div>
        {known_conditions && known_conditions.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '6px' }}>
            {known_conditions.map((c, idx) => (
              <span key={idx} className="ctx-tag-red">{c}</span>
            ))}
          </div>
        ) : (
          <div className="ctx-value-muted">None reported</div>
        )}
      </div>

      {/* Lab Results */}
      <div className="ctx-card">
        <div className="ctx-label"><FileText size={14} color="#10b981" /> Laboratory Values</div>
        {lab_results && Object.keys(lab_results).length > 0 ? (
          <div style={{ marginTop: '6px', fontSize: '0.8rem' }}>
            {Object.entries(lab_results).map(([k, v], idx) => (
              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', color: '#cbd5e1', padding: '2px 0' }}>
                <span style={{ fontWeight: 600 }}>{k}:</span>
                <span style={{ color: '#34d399' }}>{v}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="ctx-value-muted">No lab values parsed</div>
        )}
      </div>
    </div>
  );
};
