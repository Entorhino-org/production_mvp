import React, { useState } from 'react';
import { 
  X, 
  Check, 
  Filter, 
  Lightbulb,
  ChevronRight
} from 'lucide-react';
import './TeacherJoinRequests.css';

const TeacherJoinRequests = () => {
  const [requests, setRequests] = useState([
    { id: 1, name: 'Ethan Caldwell', gpa: '3.8', date: 'OCT 12', class: 'Advanced Physics II', status: 'pending', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop' },
    { id: 2, name: 'Maya Rodriguez', gpa: '4.0', date: 'OCT 14', class: 'Quantum Mechanics', status: 'pending', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop' },
    { id: 3, name: 'Leo Sterling', gpa: '3.5', date: 'OCT 15', class: 'Digital Logic System', status: 'pending', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop' },
    { id: 4, name: 'Sarah Jenkins', gpa: '3.2', date: 'OCT 18', class: 'Advanced Physics II', status: 'conflict', avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop', conflictReason: 'CONFLICT' },
  ]);

  return (
    <div className="tjr-container">
      {/* Header */}
      <div className="tjr-header-area">
        <div className="tjr-header-left">
          <h2 className="tjr-title">Join Requests</h2>
          <p className="tjr-subtitle">Review and manage pending applications for your upcoming cohorts.</p>
        </div>
        <div className="tjr-header-actions">
          <button className="tjr-btn-secondary">
            <Filter size={16} /> TOTAL PENDING
          </button>
          <button className="tjr-text-link">Batch Actions</button>
        </div>
      </div>

      <div className="tjr-content-grid">
        
        {/* Left Column - Requests List */}
        <div className="tjr-main-col">
          <div className="tjr-requests-list">
            {requests.map(req => (
              <div key={req.id} className={`tjr-req-card ${req.status === 'conflict' ? 'border-red' : 'border-green'}`}>
                <div className="tjr-req-info-area">
                  <img src={req.avatar} alt={req.name} className="tjr-req-avatar" />
                  <div className="tjr-req-details">
                    <div className="tjr-req-name-row">
                      <h4 className="tjr-req-name">{req.name}</h4>
                      {req.conflictReason && <span className="tjr-badge-conflict">{req.conflictReason}</span>}
                    </div>
                    <p className="tjr-req-meta">GPA: {req.gpa} | APPLIED {req.date}</p>
                  </div>
                </div>
                
                <div className="tjr-req-class-area">
                  <span className="tjr-class-label">REQUESTED CLASS</span>
                  <p className="tjr-class-name">{req.class}</p>
                </div>
                
                <div className="tjr-req-actions">
                  <button className="tjr-reject-btn" aria-label="Reject">
                    <X size={16} />
                  </button>
                  {req.status === 'conflict' ? (
                    <button className="tjr-resolve-btn">Resolve</button>
                  ) : (
                    <button className="tjr-approve-btn">
                      Approve <Check size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column - Stats & Info */}
        <div className="tjr-side-col">
          
          {/* Approval Analytics Card */}
          <div className="tjr-analytics-card">
            <div className="tjr-analytic-header">
              <span className="tjr-analytic-label">APPROVAL ANALYTICS</span>
            </div>
            
            <div className="tjr-capacity-row">
              <span className="tjr-cap-label">Capacity Utilized</span>
              <span className="tjr-cap-value">78%</span>
            </div>
            
            <div className="tjr-progress-track">
              <div className="tjr-progress-fill" style={{ width: '78%' }}></div>
            </div>
            
            <div className="tjr-stats-grid">
              <div className="tjr-stat-item">
                <span className="tjr-stat-big">124</span>
                <span className="tjr-stat-small">TOTAL STUDENTS</span>
              </div>
              <div className="tjr-stat-item">
                <span className="tjr-stat-big green">+14</span>
                <span className="tjr-stat-small green-sub">APPROVED TODAY</span>
              </div>
            </div>
          </div>

          {/* Class Availability Card */}
          <div className="tjr-box tjr-availability-box">
            <h4 className="tjr-box-title">CLASS AVAILABILITY</h4>
            <div className="tjr-avail-list">
              <div className="tjr-avail-row">
                <span className="tjr-avail-name">Advanced Physics II</span>
                <span className="tjr-badge-green">3 SEATS LEFT</span>
              </div>
              <div className="tjr-avail-row">
                <span className="tjr-avail-name">Quantum Mechanics</span>
                <span className="tjr-badge-green">7 SEATS LEFT</span>
              </div>
              <div className="tjr-avail-row">
                <span className="tjr-avail-name">Digital Logic System</span>
                <span className="tjr-badge-red">FULL</span>
              </div>
            </div>
          </div>

          {/* Quick Tip Box */}
          <div className="tjr-tip-box">
            <div className="tjr-tip-header">
              <Lightbulb size={20} className="tjr-tip-icon" />
              <h4>Quick Tip</h4>
            </div>
            <p>You can set up Auto-Approve rules for students with a GPA higher than 3.5 in your department.</p>
            <button className="tjr-link-btn">CONFIGURE RULES</button>
          </div>

        </div>

      </div>
    </div>
  );
};

export default TeacherJoinRequests;
