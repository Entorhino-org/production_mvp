/* ActiveTaskMainCard.jsx */
import React from 'react';
import { Clock, Play, ChevronRight } from 'lucide-react';

const ActiveTaskMainCard = ({ title, sub, priority, due, progress, avatars }) => {
  return (
    <div className="main-task-card">
      <div className="card-top">
        <span className="priority-tag">{priority}</span>
        <span className="due-info"><Clock size={12} /> Due in {due}</span>
      </div>
      
      <h2>{title}</h2>
      <p>{sub}</p>

      <div className="task-footer">
        <div className="avatars-mini">
          {avatars.map((url, i) => (
            <img key={i} src={url} alt="collaborator" className="avatar-img" />
          ))}
          <div className="avatar-img" style={{ background: '#222', fontSize: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '800' }}>+2</div>
        </div>
        
        <button className="btn-resume">
          Resume Task <Play size={12} fill="white" />
        </button>
      </div>

      <div className="progress-section">
        <div className="progress-meta">
          <span>COMPLETION STATUS</span>
          <span>{progress}%</span>
        </div>
        <div className="progress-bar-full">
          <div className="progress-fill-purple" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
};

export default ActiveTaskMainCard;
