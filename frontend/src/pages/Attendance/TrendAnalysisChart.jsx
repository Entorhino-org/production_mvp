/* TrendAnalysisChart.jsx */
import React from 'react';
import { TrendingUp } from 'lucide-react';

const TrendAnalysisChart = ({ data, diff, summary }) => {
  return (
    <div className="trend-card">
      <div className="trend-head">
        <h3>Trend Analysis</h3>
        <div className="trend-badge">
          <TrendingUp size={12} /> +{diff}%
        </div>
      </div>

      <div className="bar-chart-container">
        {data.map((val, idx) => (
          <div key={idx} className="chart-bar" style={{ height: '100px' }}>
            <div className="bar-fill" style={{ height: `${val}%`, opacity: idx === data.length - 1 ? 1 : 0.4 }} />
          </div>
        ))}
      </div>

      <p className="trend-footer-text" dangerouslySetInnerHTML={{ __html: summary }} />
    </div>
  );
};

export default TrendAnalysisChart;
