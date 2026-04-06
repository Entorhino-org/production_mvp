/* FacultyQuoteCard.jsx */
import React from 'react';

const FacultyQuoteCard = () => {
  return (
    <div className="faculty-card">
      <div className="fac-profile">
        <img 
          className="fac-img" 
          src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&q=80" 
          alt="faculty" 
        />
        <div className="fac-info">
          <h4>Dr. Sarah Vance</h4>
          <span>Physics Faculty</span>
        </div>
      </div>

      <blockquote className="fac-quote">
        "Feedback is the breakfast of champions. Your input directly impacts our curriculum updates."
      </blockquote>

      <div className="goal-box">
        <div className="goal-bar">
          <div className="goal-fill" />
        </div>
        <div className="goal-text">75% Feedback Goal Reached</div>
      </div>
    </div>
  );
};

export default FacultyQuoteCard;
