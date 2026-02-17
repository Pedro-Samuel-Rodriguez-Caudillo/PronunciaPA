import React from 'react';

interface CountdownProps {
  value: number | null;
}

export const Countdown: React.FC<CountdownProps> = ({ value }) => {
  if (value === null) return null;

  return (
    <div className="countdown-overlay" role="alert" aria-live="assertive">
      <span className="countdown-number" key={value}>
        {value}
      </span>
    </div>
  );
};
