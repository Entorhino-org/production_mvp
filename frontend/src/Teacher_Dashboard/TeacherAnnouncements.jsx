import React, { useState } from 'react';
import { 
  Megaphone, 
  Paperclip, 
  Image as ImageIcon, 
  Send, 
  Filter, 
  MoreVertical, 
  AlertTriangle, 
  FileText, 
  Clock, 
  ChevronDown
} from 'lucide-react';
import './TeacherAnnouncements.css';

const TeacherAnnouncements = () => {
  const [title, setTitle] = useState('');
  const [audience, setAudience] = useState('All Classes');
  const [priority, setPriority] = useState('Standard');
  const [content, setContent] = useState('');

  const historyData = [
    {
      id: 1,
      type: 'active',
      status: 'ACTIVE',
      time: '2 HOURS AGO',
      reads: 102,
      title: 'Revision Materials for Chapter 4: Thermodynamics',
      description: "The supplementary reading for next week's seminar has been uploaded to the shared drive. Please ensure you hav...",
      image: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=100&h=100&fit=crop',
      actionType: 'analytics'
    },
    {
      id: 2,
      type: 'urgent',
      status: 'URGENT',
      time: 'YESTERDAY',
      reads: 942,
      title: 'Emergency Drill Scheduled for Friday morning',
      description: 'All faculty and students in the Science Wing are required to participate in a mandatory safety drill at 10:15 AM. Please...',
      icon: <AlertTriangle size={24} color="#ef4444" />,
      actionType: 'attachment',
      attachmentName: 'DRILL GUIDELINES.PDF'
    },
    {
      id: 3,
      type: 'standard',
      status: 'STANDARD',
      time: '3 DAYS AGO',
      reads: 210,
      title: 'Guest Speaker: Dr. Elena Vanz on Space-Time Curvature',
      description: 'We are thrilled to host Dr. Vanz for a special lecture this Thursday. Attendance is highly encouraged for senior...',
      image: 'https://images.unsplash.com/photo-1596423735880-5f2a689b903e?w=100&h=100&fit=crop',
      actionType: 'event',
      eventTime: 'Thursday, 2:00 PM - Main Hall'
    }
  ];

  return (
    <div className="ta-container">
      {/* Header */}
      <div className="ta-header">
        <div>
          <h2 className="ta-title">Broadcasting Center</h2>
          <p className="ta-subtitle">Keep your students informed and engaged with curated updates.</p>
        </div>
        <div className="ta-reach-badge">
          <span className="ta-reach-label">ACTIVE REACH</span>
          <span className="ta-reach-value">1,248</span>
        </div>
      </div>

      <div className="ta-content-grid">
        
        {/* Left Column: Post Announcement */}
        <div className="ta-post-card">
          <div className="ta-card-header">
            <div className="ta-card-icon-bg">
              <Megaphone size={18} color="var(--td-accent)" />
            </div>
            <h3>Post Announcement</h3>
          </div>

          <div className="ta-form-group">
            <label>ANNOUNCEMENT TITLE</label>
            <input 
              type="text" 
              placeholder="e.g., Final Exam Preparation Workshop" 
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="ta-form-row">
            <div className="ta-form-group">
              <label>TARGET AUDIENCE</label>
              <div className="ta-select-wrapper">
                <select value={audience} onChange={(e) => setAudience(e.target.value)}>
                  <option>All Classes</option>
                  <option>Molecular Biology 401</option>
                  <option>Quantum Mechanics II</option>
                </select>
                <ChevronDown size={14} className="ta-select-icon" />
              </div>
            </div>
            <div className="ta-form-group">
              <label>PRIORITY</label>
              <div className="ta-select-wrapper">
                <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option>Standard</option>
                  <option>High</option>
                  <option>Urgent</option>
                </select>
                <ChevronDown size={14} className="ta-select-icon" />
              </div>
            </div>
          </div>

          <div className="ta-form-group">
            <label>CONTENT</label>
            <textarea 
              placeholder="Share updates, links, or instructions..."
              rows={6}
              value={content}
              onChange={(e) => setContent(e.target.value)}
            ></textarea>
          </div>

          <div className="ta-form-actions">
            <div className="ta-action-icons">
              <button className="ta-icon-btn" aria-label="Attach File"><Paperclip size={18} /></button>
              <button className="ta-icon-btn" aria-label="Attach Image"><ImageIcon size={18} /></button>
            </div>
            <button className="ta-submit-btn">
              Broadcast Now <Send size={16} />
            </button>
          </div>
        </div>

        {/* Right Column: Recent History */}
        <div className="ta-history-section">
          <div className="ta-history-header">
            <h3>Recent History</h3>
            <div className="ta-history-actions">
              <button className="ta-icon-btn"><Filter size={18} /></button>
              <button className="ta-icon-btn"><MoreVertical size={18} /></button>
            </div>
          </div>

          <div className="ta-history-list">
            {historyData.map((item) => (
              <div key={item.id} className={`ta-history-card border-${item.type}`}>
                <div className="ta-card-layout">
                  
                  {item.image ? (
                    <div className="ta-card-media">
                      <img src={item.image} alt="Announcement thumbnail" />
                    </div>
                  ) : (
                    <div className="ta-card-iconbox bg-red-muted">
                      {item.icon}
                    </div>
                  )}

                  <div className="ta-card-content">
                    <div className="ta-card-meta">
                      <div className="ta-meta-left">
                        <span className={`ta-badge badge-${item.type}`}>{item.status}</span>
                        <span className="ta-time">{item.time}</span>
                      </div>
                      <span className="ta-reads">{item.reads} Reads</span>
                    </div>

                    <h4 className="ta-item-title">{item.title}</h4>
                    <p className="ta-item-desc">{item.description}</p>

                    <div className="ta-item-footer">
                      {item.actionType === 'analytics' && (
                        <div className="ta-analytics-action">
                          <div className="ta-mini-avatars">
                            <div className="ta-avatar-circle" style={{backgroundColor: '#e2e8f0'}}></div>
                            <div className="ta-avatar-circle" style={{backgroundColor: '#cbd5e1'}}></div>
                            <div className="ta-avatar-circle" style={{backgroundColor: '#6366f1', color: 'white'}}>+90</div>
                          </div>
                          <span className="ta-action-text blue">VIEW ANALYTICS</span>
                        </div>
                      )}

                      {item.actionType === 'attachment' && (
                        <div className="ta-attachment-action">
                          <FileText size={14} color="var(--td-blue)" />
                          <span className="ta-action-text blue">{item.attachmentName}</span>
                        </div>
                      )}

                      {item.actionType === 'event' && (
                        <div className="ta-event-action">
                          <div className="ta-event-time">
                            <Clock size={14} />
                            <span>{item.eventTime}</span>
                          </div>
                          <button className="ta-register-btn">REGISTER STUDENT LIST</button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <button className="ta-load-more-btn">
            LOAD ARCHIVED ANNOUNCEMENTS
          </button>
        </div>
      </div>
    </div>
  );
};

export default TeacherAnnouncements;
