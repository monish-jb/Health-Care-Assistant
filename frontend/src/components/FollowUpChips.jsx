import React from 'react';

export const FollowUpChips = ({ options, onSelectOption, disabled }) => {
  if (!options || options.length === 0) return null;

  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: '8px',
      marginTop: '12px',
      marginBottom: '4px'
    }}>
      {options.map((option, idx) => (
        <button
          key={idx}
          type="button"
          disabled={disabled}
          onClick={() => onSelectOption(option)}
          style={{
            background: '#F8FAFC',
            border: '1px solid #CBD5E1',
            color: '#0B5A54',
            borderRadius: '9999px',
            padding: '7px 15px',
            fontSize: '0.8rem',
            fontWeight: 700,
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }}
          onMouseEnter={(e) => {
            if (!disabled) {
              e.currentTarget.style.background = '#E3F3F1';
              e.currentTarget.style.borderColor = '#0B5A54';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled) {
              e.currentTarget.style.background = '#F8FAFC';
              e.currentTarget.style.borderColor = '#CBD5E1';
              e.currentTarget.style.transform = 'none';
            }
          }}
        >
          {option}
        </button>
      ))}
    </div>
  );
};
