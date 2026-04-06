import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import RecentInteractionCard from './RecentInteractionCard';
import FacultyQuoteCard from './FacultyQuoteCard';
import FeedbackForm from './FeedbackForm';
import FeedbackMetricsRow from './FeedbackMetricsRow';
import { MessageCircle, ShieldCheck } from 'lucide-react';
import './Feedback.css';

const FeedbackPage = ({ user }) => {
  const navigate = useNavigate();
  const interactions = []; // Empty for starting users

  return (
    <div className="fb-container">
      {/* Header */}
      <header className="fb-header">
        <h1>Give Feedback</h1>
        <p>Your voice fuels our growth. Help us shape the future of your learning experience.</p>
      </header>

      {/* Main Form Area */}
      <div className="fb-grid">
        <aside className="fb-side">
          {interactions.length > 0 ? (
            <RecentInteractionCard />
          ) : (
             <div className="fb-info-card">
                <ShieldCheck size={32} color="var(--neon-green)" />
                <h4>Secure & Anonymous</h4>
                <p>Your feedback is used only to improve the educational output. It's stored securely and reviewed by the academic panel.</p>
             </div>
          )}
          
          <FacultyQuoteCard 
            quote="Constructive critique is the foundation of institutional excellence." 
            author="Academic Board" 
          />
        </aside>

        <section className="fb-main">
          <FeedbackForm user={user} />
        </section>
      </div>

      {/* Metrics or Message */}
      <div className="fb-footer-note">
        <MessageCircle size={18} opacity={0.6} />
        <p>Completed your recently assigned surveys? All entries help Entorhino's engine evolve.</p>
      </div>
    </div>
  );
};

export default FeedbackPage;
