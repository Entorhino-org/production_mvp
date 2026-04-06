/* FeaturedUpdateCard.jsx */
import React from 'react';
import { Star } from 'lucide-react';

const FeaturedUpdateCard = ({ title, desc, date, badge }) => {
  return (
    <div className="featured-card">
      <div className="feat-content">
        <span className="feat-badge">{badge}</span>
        <h2 className="feat-title">{title}</h2>
        <p className="feat-desc">{desc}</p>
        <div className="feat-actions">
          <button className="btn-neon">Register Now</button>
          <button className="btn-glass">View Details</button>
        </div>
      </div>
      <div className="feat-visual">
         <div className="feat-date">
            <span style={{ display: 'block', fontWeight: 800 }}>OCT 24,</span>
            <span>2023</span>
         </div>
      </div>
      <div style={{ position: 'absolute', top: 38, left: 38, opacity: 0.1 }}>
        <Star size={48} fill="#fff" />
      </div>
    </div>
  );
};

export default FeaturedUpdateCard;
