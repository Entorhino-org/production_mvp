import React, { useState } from 'react';
import { 
  ChevronDown, 
  Filter, 
  TrendingUp, 
  Star, 
  MoreVertical,
  ExternalLink
} from 'lucide-react';
import './TeacherInsights.css';

const TeacherInsights = () => {
  const [section, setSection] = useState('Section A - Advanced');
  const [subject, setSubject] = useState('Quantum Physics II');

  const topics = [
    { name: 'Quantum Entanglement', score: 94, color: 'var(--td-blue)' },
    { name: 'Wave-Particle Duality', score: 78, color: 'var(--td-accent)' },
    { name: "Schrödinger's Equation", score: 86, color: 'var(--td-green)' },
    { name: 'Heisenberg Uncertainty', score: 43, color: 'var(--td-red)' },
  ];

  const leaders = [
    { initials: 'JD', name: 'Julianne Davis', avg: '98.2% GRADE AVG', color: '#818cf8' },
    { initials: 'MK', name: 'Marcus Kane', avg: '95.1% GRADE AVG', color: '#a78bfa' },
    { initials: 'SW', name: 'Sarah Williams', avg: '94.0% GRADE AVG', color: '#34d399' },
  ];

  const students = [
    { initials: 'AL', name: 'Amara Ling', attendance: '98%', test: 'A+', testColor: 'var(--td-blue)', risk: 'STABLE', riskColor: 'green' },
    { initials: 'BK', name: 'Benson Knight', attendance: '72%', test: 'C-', testColor: 'var(--td-red)', risk: 'AT RISK', riskColor: 'red' },
    { initials: 'CR', name: 'Cora Ritz', attendance: '89%', test: 'B+', testColor: 'var(--td-accent)', risk: 'NEUTRAL', riskColor: 'gray' },
  ];

  const bars = [40, 70, 55, 85, 60, 30, 0]; // heights in %

  return (
    <div className="ti-container">
      {/* Header */}
      <div className="ti-header-area">
        <div className="ti-header-left">
          <h2 className="ti-title">Class Insights</h2>
          <p className="ti-subtitle">Detailed performance tracking and cohort analysis</p>
        </div>
        <div className="ti-header-actions">
          <div className="ti-filter-group">
            <span className="ti-filter-label">SECTION</span>
            <div className="ti-select-wrapper">
              <select value={section} onChange={(e) => setSection(e.target.value)}>
                <option>Section A - Advanced</option>
                <option>Section B - Core</option>
              </select>
              <ChevronDown size={14} className="ti-select-icon" />
            </div>
          </div>
          <div className="ti-filter-group">
            <span className="ti-filter-label">SUBJECT</span>
            <div className="ti-select-wrapper">
              <select value={subject} onChange={(e) => setSubject(e.target.value)}>
                <option>Quantum Physics II</option>
                <option>Advanced Calculus</option>
              </select>
              <ChevronDown size={14} className="ti-select-icon" />
            </div>
          </div>
          <button className="ti-icon-btn">
            <Filter size={16} />
          </button>
        </div>
      </div>

      <div className="ti-content-grid">
        
        {/* Top Row */}
        <div className="ti-top-row">
          {/* Average Score Card */}
          <div className="ti-card ti-avg-card">
            <h4 className="ti-card-title">CLASS AVERAGE SCORE</h4>
            <div className="ti-score-display">
              <span className="ti-big-score">84.2%</span>
              <span className="ti-trend-up"><TrendingUp size={14} /> +3.4%</span>
            </div>
            
            <div className="ti-progress-wrapper">
              <div className="ti-progress-labels">
                <span>Progress toward target (90%)</span>
                <span>93%</span>
              </div>
              <div className="ti-progress-track">
                <div className="ti-progress-fill" style={{ width: '93%' }}></div>
              </div>
            </div>
          </div>

          {/* Engagement Overview Card */}
          <div className="ti-card ti-chart-card">
            <div className="ti-card-header">
              <div>
                <span className="ti-card-super">ENGAGEMENT OVERVIEW</span>
                <h4 className="ti-card-title" style={{ marginTop: '2px' }}>Weekly Attendance & Participation</h4>
              </div>
              <div className="ti-legend">
                <div className="ti-legend-item"><div className="ti-dot blue"></div> Lecture</div>
                <div className="ti-legend-item"><div className="ti-dot green"></div> Lab</div>
              </div>
            </div>
            
            <div className="ti-bar-chart">
              {bars.map((h, i) => (
                <div key={i} className="ti-bar-wrapper">
                  <div className="ti-bar" style={{ height: `${h}%` }}></div>
                </div>
              ))}
            </div>
            <div className="ti-chart-labels">
              <span>MON</span>
              <span>TUE</span>
              <span>WED</span>
              <span>THU</span>
              <span>FRI</span>
              <span>SAT</span>
              <span>SUN</span>
            </div>
          </div>
        </div>

        {/* Middle Row */}
        <div className="ti-mid-row">
          {/* Topic Mastery */}
          <div className="ti-card ti-topics-card">
            <div className="ti-card-header">
              <h3 className="ti-section-title">Topic Mastery Breakdown</h3>
              <button className="ti-text-link">View All Topics &gt;</button>
            </div>
            
            <div className="ti-topics-list">
              {topics.map((topic, i) => (
                <div key={i} className="ti-topic-item">
                  <div className="ti-topic-labels">
                    <span className="ti-topic-name">{topic.name}</span>
                    <span className="ti-topic-score" style={{ color: topic.color }}>{topic.score}%</span>
                  </div>
                  <div className="ti-topic-track">
                    <div className="ti-topic-fill" style={{ width: `${topic.score}%`, backgroundColor: topic.color }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cohort Leaders */}
          <div className="ti-card ti-leaders-card">
            <h3 className="ti-section-title">Cohort Leaders</h3>
            <div className="ti-leaders-list">
              {leaders.map((leader, i) => (
                <div key={i} className="ti-leader-item">
                  <div className="ti-leader-info">
                    <div className="ti-initials" style={{ backgroundColor: `${leader.color}20`, color: leader.color }}>
                      {leader.initials}
                    </div>
                    <div>
                      <div className="ti-leader-name">{leader.name}</div>
                      <div className="ti-leader-avg">{leader.avg}</div>
                    </div>
                  </div>
                  <Star size={16} color="var(--td-green)" fill="var(--td-green)" />
                </div>
              ))}
            </div>
            <button className="ti-full-btn">View Full Leaderboard</button>
            <button className="ti-export-fab"><ExternalLink size={18} /></button>
          </div>
        </div>

        {/* Bottom Row */}
        <div className="ti-card ti-matrix-card">
          <div className="ti-matrix-header">
            <h3 className="ti-section-title">Student Insight Matrix</h3>
            <div className="ti-matrix-actions">
              <button className="ti-btn-secondary">Export CSV</button>
              <button className="ti-btn-primary">Send Batch Alert</button>
            </div>
          </div>

          <div className="ti-table-wrapper">
            <table className="ti-table">
              <thead>
                <tr>
                  <th>STUDENT NAME</th>
                  <th>ATTENDANCE</th>
                  <th>LAST TEST</th>
                  <th>RISK LEVEL</th>
                  <th className="align-right">ACTION</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s, i) => (
                  <tr key={i}>
                    <td>
                      <div className="ti-student-cell">
                        <div className="ti-small-initials">{s.initials}</div>
                        <span>{s.name}</span>
                      </div>
                    </td>
                    <td className="ti-cell-text">{s.attendance}</td>
                    <td style={{ color: s.testColor, fontWeight: '700' }}>{s.test}</td>
                    <td>
                      <span className={`ti-risk-badge badge-${s.riskColor}`}>{s.risk}</span>
                    </td>
                    <td className="align-right">
                      <button className="ti-action-btn"><MoreVertical size={16} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className="ti-load-link">LOAD COMPLETE ROSTER</button>
        </div>

      </div>
    </div>
  );
};

export default TeacherInsights;
