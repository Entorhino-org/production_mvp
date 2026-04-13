import React from 'react';
import { 
  BellOff, 
  ChevronDown, 
  Sparkles, 
  ArrowRight 
} from 'lucide-react';
import './TeacherAlerts.css';

const TeacherAlerts = () => {
  return (
    <div className="tal-container">
      {/* Header */}
      <div className="tal-header-area">
        <div className="tal-header-left">
          <span className="tal-super-title">SYSTEM MONITORING</span>
          <h2 className="tal-title">Smart Alerts</h2>
          <p className="tal-subtitle">Real-time pedagogical notifications, student performance triggers, and administrative updates curated for your focus.</p>
        </div>
        <div className="tal-header-actions">
          <button className="tal-btn-outline">Mark all read</button>
          <button className="tal-btn-dark">
            <ChevronDown size={16} /> Configure Rules
          </button>
        </div>
      </div>

      <div className="tal-content-grid">
        
        {/* Left Main Area: Empty State */}
        <div className="tal-main-col">
          <div className="tal-empty-state">
            <div className="tal-icon-wrapper">
              <BellOff size={32} color="var(--td-accent)" />
            </div>
            <h3 className="tal-empty-title">No alerts</h3>
            <p className="tal-empty-desc">
              Your dashboard is currently clear. We'll notify you when student performance shifts or deadlines approach.
            </p>
            
            <div className="tal-suggestions">
              <span className="tal-suggestions-label">SUGGESTED QUICK ACTIONS</span>
              <div className="tal-suggestion-buttons">
                <button className="tal-pill-btn">Review Attendance</button>
                <button className="tal-pill-btn">Check Grades</button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side Cards */}
        <div className="tal-side-col">
          
          {/* Smart Context Box */}
          <div className="tal-box">
            <div className="tal-box-header">
              <Sparkles size={14} color="var(--td-blue)" />
              <span className="tal-box-super">SMART CONTEXT</span>
            </div>
            <h4 className="tal-context-title">Quiet periods are great for curriculum planning.</h4>
            <p className="tal-context-desc">
              Based on your historical data, Tuesdays are your most productive days for content creation.
            </p>
            <button className="tal-link-btn">
              Open Curators Toolkit <ArrowRight size={14} />
            </button>
          </div>

          {/* Class Health Box */}
          <div className="tal-box tal-border-green">
            <div className="tal-health-header">
              <span className="tal-box-super">CLASS HEALTH</span>
              <span className="tal-badge-stable">STABLE</span>
            </div>
            <div className="tal-health-score">
              <span className="tal-score-big">98%</span>
              <span className="tal-score-trend">+2%</span>
            </div>
            <p className="tal-health-desc">Overall engagement across 4 active classes.</p>
          </div>

          {/* Priority Rules Dark Box */}
          <div className="tal-dark-box">
            <h4 className="tal-dark-title">Priority Rules</h4>
            <p className="tal-dark-desc">Currently active triggers for your dashboard:</p>
            
            <ul className="tal-rules-list">
              <li>
                <div className="tal-dot gray"></div>
                Grade drops &gt; 15%
              </li>
              <li>
                <div className="tal-dot green"></div>
                Missed attendance (2 days)
              </li>
              <li>
                <div className="tal-dot red"></div>
                Urgent faculty notices
              </li>
            </ul>

            <button className="tal-dark-btn-outline">Manage Triggers</button>
          </div>

        </div>

      </div>
    </div>
  );
};

export default TeacherAlerts;
