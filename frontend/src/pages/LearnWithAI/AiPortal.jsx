import React, { useState } from 'react';
import { Search, Bell, Zap, MessageSquarePlus, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import NeuralChatWindow from './NeuralChatWindow';
import AcceleratedPathCard from './AcceleratedPathCard';
import LearningMomentumStat from './LearningMomentumStat';
import './AiPortal.css';

const AiPortal = ({ user }) => {
  const navigate = useNavigate();
  const firstName = user?.full_name?.split(' ')[0] || 'User';

  const [chatHistory, setChatHistory] = useState([
    { 
      role: 'ai', 
      text: `Hello ${firstName}! I am your personal AI tutor. I have analyzed your curriculum. What would you like to master today?`,
      type: 'text'
    }
  ]);

  const handleNewChat = () => {
    setChatHistory([
      { 
        role: 'ai', 
        text: `Starting a fresh session. How can I assist you in your studies today, ${firstName}?`,
        type: 'text'
      }
    ]);
  };

  const paths = []; // Empty for new users

  return (
    <div className="ai-portal-container">
      {/* Header */}
      <header className="ai-header">
        <div className="search-ai">
          <Search size={14} opacity={0.5} />
          <input type="text" placeholder="Ask AI anything about your curriculum..." />
        </div>
        <div className="ai-user-profile">
          <Bell size={18} opacity={0.6} style={{ cursor: 'pointer' }} onClick={() => navigate('/alerts')} />
          <div className="ai-user-text" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
            <span className="ai-user-name">{user?.full_name || 'Scholar'}</span>
            <span className="ai-user-rank">RANK: PENDING</span>
          </div>
          <img 
            src={`https://ui-avatars.com/api/?name=${user?.full_name || 'User'}&background=A855F7&color=fff`} 
            alt="profile" 
            style={{ width: '32px', height: '32px', borderRadius: '50%', border: '1.5px solid var(--neon-purple)', cursor: 'pointer' }} 
            onClick={() => navigate('/')}
          />
        </div>
      </header>

      {/* Hero */}
      <div className="ai-hero">
        <div className="ai-hero-text">
          <h1>Learn with <span>AI</span></h1>
          <p>Your personalized cognitive accelerator.</p>
        </div>
        <div className="ai-actions-row">
            <button className="new-chat-btn" onClick={handleNewChat}>
              <MessageSquarePlus size={16} /> NEW CHAT
            </button>
            <div className="ai-engine-status">
              <Zap size={12} fill="currentColor" /> AI ENGINE ACTIVE
            </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="ai-grid">
        <section className="col-chat">
          <NeuralChatWindow messages={chatHistory} setMessages={setChatHistory} />
        </section>

        <aside className="ai-sidebar">
          <div className="path-section-head">
            <h3>Accelerated Paths</h3>
          </div>
          
          {paths.length > 0 ? (
            paths.map((p, idx) => <AcceleratedPathCard key={idx} {...p} />)
          ) : (
            <div className="sidebar-empty-box">
              <Info size={24} opacity={0.3} />
              <p>Paths are generated based on your weak topics. Take a test to unlock.</p>
            </div>
          )}
          
          <LearningMomentumStat xp={0} />
        </aside>
      </div>
    </div>
  );
};

export default AiPortal;
