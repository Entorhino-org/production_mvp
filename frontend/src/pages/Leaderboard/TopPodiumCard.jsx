/* TopPodiumCard.jsx */
import React from 'react';

const TopPodiumCard = ({ rank, name, subject, xp, tags, avatar, badge, type }) => {
  return (
    <div className={`podium-card rank-${rank}`}>
      {badge && <div className={`champ-badge ${type}`}>{badge}</div>}
      <div className="lb-avatar-box">
        <img src={avatar} alt={name} className="lb-avatar" />
        <div className="rank-number-tag">{rank}</div>
      </div>
      <h4>{name}</h4>
      <div className="p-subj">{subject}</div>
      <div className="p-xp">{xp.toLocaleString()}<span>XP</span></div>
      {tags && (
        <div className="podium-tags">
          {tags.map((t, idx) => (
             <span key={idx} className={`p-tag ${t.color}`}>{t.label}</span>
          ))}
        </div>
      )}
    </div>
  );
};

export default TopPodiumCard;
