/* FeedbackMetricsRow.jsx */
import React from 'react';
import { Clock, CheckCircle, Award } from 'lucide-react';

const FeedbackMetricsRow = () => {
  return (
    <div className="fb-metrics-row">
      <div className="metric-item">
        <div className="metric-icon clock"><Clock size={20} /></div>
        <div className="metric-data">
          <h5>Avg Response</h5>
          <span>24 Hours</span>
        </div>
      </div>

      <div className="metric-item">
        <div className="metric-icon check"><CheckCircle size={20} /></div>
        <div className="metric-data">
          <h5>Success Rate</h5>
          <span>98% Resolved</span>
        </div>
      </div>

      <div className="metric-item">
        <div className="metric-icon medal"><Award size={20} /></div>
        <div className="metric-data">
          <h5>Total Rewarded</h5>
          <span>450 Tokens</span>
        </div>
      </div>
    </div>
  );
};

export default FeedbackMetricsRow;
