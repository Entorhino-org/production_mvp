import React, { useState, useEffect } from 'react';
import { Search, Bell, Sigma, Microscope, BookOpen, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AssignedHomeworkHero from './AssignedHomeworkHero';
import ActiveTaskMainCard from './ActiveTaskMainCard';
import SecondaryTaskCard from './SecondaryTaskCard';
import VelocityStatsCard from './VelocityStatsCard';
import DeadlineWarningStrip from './DeadlineWarningStrip';
import CompletedTaskListItem from './CompletedTaskListItem';
import analyticsService from '../../api/analytics';
import './HomeworkPortal.css';

const HomeworkPortal = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHomework = async () => {
      try {
        setLoading(true);
        if (user?.id) {
          const res = await analyticsService.getStudentDashboard(user.id);
          setData(res);
        }
      } catch (err) {
        console.error('Failed to fetch homework:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchHomework();
  }, [user?.id]);

  const hasData = data && data.recent_homework?.length > 0;

  return (
    <div className="homework-container">
      {/* Search & Profile Row */}
      <header className="hw-header">
        <div className="search-assignments">
          <Search size={14} opacity={0.5} />
          <input type="text" placeholder="Search tasks..." />
        </div>
        <div className="user-profile-mini">
          <Bell 
            size={18} 
            opacity={0.6} 
            style={{ marginRight: '10px', cursor: 'pointer' }} 
            onClick={() => navigate('/alerts')}
          />
          <div 
            className="user-text-box" 
            style={{ cursor: 'pointer' }}
            onClick={() => navigate('/')}
          >
            <span className="user-name">{user?.full_name || 'Scholar'}</span>
            <span className="user-level">{user?.role || 'STUDENT'}</span>
          </div>
          <img 
             src={`https://ui-avatars.com/api/?name=${user?.full_name || 'User'}&background=A855F7&color=fff`} 
            alt="profile" 
            className="profile-avatar" 
            style={{ cursor: 'pointer' }}
            onClick={() => navigate('/')}
          />
        </div>
      </header>

      {/* Hero Stats */}
      <AssignedHomeworkHero count={data?.recent_homework?.length || 0} />

      {!hasData && !loading ? (
        <div className="portal-empty-state">
           <div className="empty-content">
            <div className="empty-icon-pulse">
              <BookOpen size={48} color="var(--neon-purple)" />
            </div>
            <h2>No Homework Assigned</h2>
            <p>You have zero pending tasks at the moment. Take this time to review your previous chapters or explore AI learning modules.</p>
            <div className="empty-info-card">
              <Info size={16} />
              <span>New assignments will appear here once published by your teachers.</span>
            </div>
            <button className="empty-cta-btn" onClick={() => navigate('/ai-portal')}>
              EXPLORE AI LEARNING
            </button>
          </div>
        </div>
      ) : loading ? (
        <div className="portal-loading">
          <div className="neon-spinner"></div>
          <p>Scanning assignments backlog...</p>
        </div>
      ) : (
        <>
          {/* Main Grid: Active Tasks */}
          <div className="hw-grid">
            {data.recent_homework.slice(0, 1).map((hw, idx) => (
               <ActiveTaskMainCard 
                key={idx}
                title={hw.title}
                sub={hw.ai_feedback || 'Submission pending final AI review.'}
                priority="RECENT"
                due="Check Details"
                progress={hw.score}
                avatars={[]}
              />
            ))}
            
            <div className="side-tasks">
              <VelocityStatsCard pct={data.homework_average} />
            </div>
          </div>

          {/* Lower Grid */}
          <div className="lower-grid">
            <section className="completed-section-mini" style={{ gridColumn: '1 / -1' }}>
              <div className="completed-head-mini">
                <h2>Recent <span>Submissions</span></h2>
              </div>
              
              <div className="completed-list">
                {data.recent_homework.map((hw, idx) => (
                  <CompletedTaskListItem 
                    key={idx}
                    title={hw.title}
                    sub={hw.ai_feedback || 'Verified Submission'}
                    grade={`${hw.score}%`}
                    date={new Date(hw.submitted_at).toLocaleDateString()}
                  />
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
};

export default HomeworkPortal;
