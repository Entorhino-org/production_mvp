/* PulsePredictionBanner.jsx */
import React from 'react';
import { Zap } from 'lucide-react';

const PulsePredictionBanner = ({ name, prediction, onAction }) => {
  return (
    <div className="lb-pulse-banner">
      <div className="pulse-icon-box"><Zap size={20} fill="currentColor" /></div>
      <div className="pulse-text" dangerouslySetInnerHTML={{ __html: `<b>Pulse Prediction:</b> ${name}, ${prediction}` }} />
      <button className="btn-roadmap" onClick={onAction}>View Roadmap</button>
    </div>
  );
};

export default PulsePredictionBanner;
