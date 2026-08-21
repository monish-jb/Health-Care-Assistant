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
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            color: '#34d399',
            borderRadius: '20px',
            padding: '6px 14px',
            fontSize: '0.825rem',
            fontWeight: 500,
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease',
            boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
          }}
          onMouseEnter={(e) => {
            if (!disabled) {
              e.currentTarget.style.background = 'rgba(16, 185, 129, 0.25)';
              e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.6)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }
          }}
          onMouseLeave={(e) => {
            if (!disabled) {
              e.currentTarget.style.background = 'rgba(16, 185, 129, 0.12)';
              e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.35)';
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
