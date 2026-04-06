/* NeuralChatWindow.jsx */
import React from 'react';
import { Bot, Mic, Paperclip, Send, Play } from 'lucide-react';
import FormattedAiResponse from './FormattedAiResponse';

const NeuralChatWindow = ({ messages }) => {
  return (
    <div className="neural-unit">
      <div className="neural-header">
        <div className="neural-title">
          <div className="neural-icon-box"><Bot size={16} /></div>
          ENTORHINO NEURAL UNIT
        </div>
        <div className="synthesis-status">
          • SYNTHESIZING CONTEXT
        </div>
      </div>

      <div className="chat-history">
        {messages.map((m, idx) => (
          <div key={idx} className={`chat-bubble ${m.role === 'ai' ? 'bubble-ai' : 'bubble-user'}`}>
             {m.role === 'ai' ? (
                <div className="ai-avatar"><Bot size={16} /></div>
             ) : (
                <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&q=80" alt="user" className="user-avatar" />
             )}
             <div className="bubble-content">
               {m.type === 'simulation' ? (
                 <>
                   <p>{m.text}</p>
                   <div className="sim-preview">
                     <img src={m.simImg} alt="sim" className="sim-img" />
                     <div className="sim-play"><Play size={20} fill="#fff" /></div>
                   </div>
                   <p style={{ marginTop: '12px', fontSize: '0.65rem', opacity: 0.6 }}>{m.simDesc}</p>
                 </>
               ) : (
                 <FormattedAiResponse content={m.text} />
               )}
             </div>
          </div>
        ))}
      </div>

      <div className="chat-input-bar">
        <div className="input-box">
          <Mic size={16} />
          <input type="text" placeholder="Type your question or choose a prompt below..." />
          <Paperclip size={16} />
        </div>
        <button className="btn-send"><Send size={18} /></button>
      </div>
    </div>
  );
};

export default NeuralChatWindow;
