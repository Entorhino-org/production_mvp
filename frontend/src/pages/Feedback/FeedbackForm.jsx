import React, { useState, useEffect } from 'react';
import { Star, CloudUpload, CheckCircle, AlertCircle } from 'lucide-react';
import communicationService from '../../api/communication';

const FeedbackForm = ({ user }) => {
  const [rating, setRating] = useState(5);
  const [teachers, setTeachers] = useState([]);
  const [selectedTeacher, setSelectedTeacher] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null); // 'success' or 'error'
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const fetchTeachers = async () => {
      try {
        const res = await communicationService.getMyTeachers();
        setTeachers(res);
        if (res.length > 0) setSelectedTeacher(res[0].id);
      } catch (err) {
        console.error('Failed to fetch teachers:', err);
      }
    };
    fetchTeachers();
  }, []);

  const handleSubmit = async () => {
    if (!selectedTeacher) {
      setErrorMsg('Please select a teacher to provide feedback.');
      setStatus('error');
      return;
    }
    if (!content.trim()) {
      setErrorMsg('Please enter your feedback message.');
      setStatus('error');
      return;
    }

    try {
      setLoading(true);
      setStatus(null);
      await communicationService.submitFeedback({
        teacher_id: selectedTeacher,
        rating: rating,
        content: content
      });
      setStatus('success');
      setContent('');
      setRating(5);
    } catch (err) {
      console.error('Feedback submission failed:', err);
      const msg = err.response?.data?.detail || 'Failed to submit feedback. Please try again.';
      setErrorMsg(msg);
      setStatus('error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fb-form">
      <div className="form-group">
        <label className="form-label">Select Faculty member</label>
        {teachers.length > 0 ? (
          <select 
            className="select-custom" 
            value={selectedTeacher} 
            onChange={(e) => setSelectedTeacher(e.target.value)}
          >
            {teachers.map(t => (
              <option key={t.id} value={t.id}>{t.full_name} ({t.subject})</option>
            ))}
          </select>
        ) : (
          <p className="no-teachers-hint">No faculty members found for your enrolled sections.</p>
        )}
      </div>

      <div className="form-group">
        <label className="form-label">Insight Rating</label>
        <div className="rating-box">
          <div className="stars-container">
            {[1, 2, 3, 4, 5].map(s => (
              <Star 
                key={s} 
                size={28} 
                fill={s <= rating ? 'var(--neon-purple)' : 'transparent'} 
                color={s <= rating ? 'var(--neon-purple)' : 'var(--text-secondary)'} 
                style={{ cursor: 'pointer', opacity: s <= rating ? 1 : 0.4 }}
                onClick={() => setRating(s)}
              />
            ))}
          </div>
          <div className="rating-summary">
            <div className="rating-num">{rating}.0</div>
            <p className="rating-desc">{rating === 5 ? 'Exceptional Performance' : rating >= 4 ? 'Very Satisfied' : 'Needs Improvement'}</p>
          </div>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Performance Details</label>
        <textarea 
          className="textarea-minimal" 
          placeholder="Describe your learning experience with this faculty in detail..." 
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
      </div>

      {status === 'success' && (
        <div className="status-msg success">
          <CheckCircle size={16} />
          <span>Feedback submitted successfully! Anonymous channel active.</span>
        </div>
      )}

      {status === 'error' && (
        <div className="status-msg error">
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="submit-bar">
        <div className="channel-status">
          <div className="status-dot" /> ENCRYPTED PIPELINE ACTIVE
        </div>
        <div className="form-actions">
           <button 
            className="btn-send-fb" 
            onClick={handleSubmit} 
            disabled={loading || teachers.length === 0}
          >
            {loading ? 'SYNCING...' : 'SEND FEEDBACK'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackForm;
