/* SubjectAttendanceBreakdown.jsx */
import React from 'react';
import { Sigma, Microscope, Laptop } from 'lucide-react';

const SubjectAttendanceBreakdown = ({ subjects }) => {
  const getIcon = (type) => {
    switch(type) {
      case 'math': return <Sigma size={18} />;
      case 'chem': return <Microscope size={18} />;
      case 'cs': return <Laptop size={18} />;
      default: return <Sigma size={18} />;
    }
  };

  return (
    <div className="subject-breakdown">
      <div className="breakdown-head">
        <h3>Subject-wise Attendance</h3>
      </div>

      <div className="subjects-list">
        {subjects.map((s, idx) => (
          <div key={idx} className="subject-item">
            <div className={`subj-icon ${s.type}`}>
              {getIcon(s.type)}
            </div>
            <div className="subj-info">
              <span className="sj-title">{s.name}</span>
              <span className="sj-sess">{s.attended} of {s.total} sessions attended</span>
            </div>
            <div className="sj-progress">
              <div 
                className="sj-fill" 
                style={{ 
                  width: `${s.pct}%`, 
                  background: s.type === 'math' ? 'var(--neon-purple)' : s.type === 'chem' ? 'var(--neon-cyan)' : 'var(--neon-green)' 
                }} 
              />
            </div>
            <span className="sj-pct" style={{ color: s.type === 'math' ? 'var(--neon-purple)' : s.type === 'chem' ? 'var(--neon-cyan)' : 'var(--neon-green)' }}>{s.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SubjectAttendanceBreakdown;
