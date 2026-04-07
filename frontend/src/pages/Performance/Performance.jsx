import React, { useState, useEffect } from 'react';
import { 
  Bell, 
  Settings, 
  Search, 
  ChevronRight, 
  Brain, 
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingDown,
  Info
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import analyticsService from '../../api/analytics';
import './Performance.css';

const Performance = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const firstName = user?.full_name?.split(' ')[0] || 'User';

  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        setLoading(true);
        if (user?.id) {
          const res = await analyticsService.getStudentDashboard(user.id);
          setData(res);
        }
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
        setError('Failed to load real-time data.');
      } finally {
        setLoading(false);
      }
    };

    fetchPerformance();
  }, [user?.id]);

  // Map API data to our UI stats
  const stats = [
    { 
      label: 'AVERAGE SCORE', 
      value: data ? `${data.average_score}%` : '0%', 
      color: '#A855F7', 
      target: '/leaderboard' 
    },
    { 
      label: 'TESTS TAKEN', 
      value: data ? String(data.total_tests_taken) : '0', 
      color: '#22D3EE', 
      target: '/tests' 
    },
    { 
      label: 'ATTENDANCE', 
      value: data ? `${data.attendance_rate}%` : '0%', 
      color: '#4ADE80', 
      target: '/attendance' 
    },
    { 
      label: 'HOMEWORK AVG', 
      value: data ? `${data.homework_average}%` : '0%', 
      color: '#6B7280', 
      target: '/homework' 
    }
  ];

  const recentUpdates = [];
  if (data?.recent_tests) {
    data.recent_tests.forEach(t => recentUpdates.push({
      name: t.test_title,
      module: 'Test Assessment',
      status: t.score >= 40 ? 'Passed' : 'Failed',
      time: 'RECENT',
      score: `${t.score}/100`,
      icon: 'Σ',
      type: 'test'
    }));
  }
  if (data?.recent_homework) {
    data.recent_homework.forEach(h => recentUpdates.push({
      name: h.title,
      module: 'Homework Submission',
      status: 'Submitted',
      time: 'RECENT',
      score: `${h.score}/100`,
      icon: '[]',
      type: 'hw'
    }));
  }

  return (
    <div className="performance-container">
      {/* Top Header */}
      <header className="header-nav">
        <div className="search-bar">
          <Search size={16} className="search-icon" />
          <input type="text" placeholder="Search insights, modules, or grades..." />
        </div>
        <div className="header-actions">
          <Bell size={20} className="icon-btn" onClick={() => navigate('/alerts')} />
          <Settings size={20} className="icon-btn" />
          <div className="user-avatar-small" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
            <img src={`https://ui-avatars.com/api/?name=${user?.full_name || 'User'}&background=A855F7&color=fff`} alt="User" />
          </div>
        </div>
      </header>

      <div className="dashboard-main">
        <div className="left-panel">
          {/* Greeting */}
          <section className="greeting">
            <h1>Morning, <span className="accent-italic">{firstName}.</span></h1>
            <p>
              {recentUpdates.length > 0 
                ? `You have ${recentUpdates.length} recent updates in your performance profile.` 
                : "Welcome! Start taking tests or submitting homework to see your insights here."}
            </p>
          </section>

          {/* Performance Rings */}
          <section className="stats-section">
            <div className="section-header">
              <h3>My Performance</h3>
              <span className="live-pulse">LIVE PULSE</span>
            </div>
            <div className="rings-grid">
              {stats.map((stat, idx) => (
                <div 
                  key={idx} 
                  className="stat-card" 
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(stat.target)}
                >
                  <div className="ring-container" style={{ borderColor: stat.color }}>
                    <span className="stat-value">{stat.value}</span>
                  </div>
                  <span className="stat-label">{stat.label}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Recent Assessments */}
          <section className="assessments-section">
            <div className="section-header">
              <h3>Recent Updates</h3>
            </div>
            
            {loading ? (
              <div className="loading-placeholder">
                <div className="pulse-loader"></div>
                <p>Syncing with Neurons...</p>
              </div>
            ) : recentUpdates.length > 0 ? (
              <div className="assessment-list">
                {recentUpdates.map((item, idx) => (
                  <motion.div 
                    key={idx} 
                    whileHover={{ scale: 1.01 }}
                    className="assessment-item"
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(item.type === 'test' ? '/tests' : '/homework')}
                  >
                    <div className="item-icon">{item.icon}</div>
                    <div className="item-info">
                      <h4>{item.name}</h4>
                      <p>{item.module}</p>
                    </div>
                    <div className="item-status">
                      <span className={item.status.toLowerCase()}>{item.status}</span>
                      <p>{item.time}</p>
                    </div>
                    <div className="item-score">{item.score}</div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">
                  <Info size={40} color="var(--neon-purple)" opacity={0.5} />
                </div>
                <h4>No recent updates</h4>
                <p>Complete your first test or homework to see analytics here.</p>
                <button className="empty-cta" onClick={() => navigate('/tests')}>
                  EXPLORE TESTS
                </button>
              </div>
            )}
          </section>
        </div>

        <div className="right-panel">
          {/* Focus Target Card */}
          <div className="focus-card">
            <div className="focus-header">
              <div className="brain-icon"><Brain size={18} /></div>
              <h3>Focus Target</h3>
            </div>
            <div className="focus-content">
              {recentUpdates.length > 0 ? (
                <>
                  <p>AI Pulse is analyzing your patterns. Consistency in <strong>Assignments</strong> could increase your readiness by <span className="green-text">+8%</span>.</p>
                  
                  <div className="progress-group">
                    <div className="label-row">
                      <span>CURRENT CONFIDENCE</span>
                      <span>{data?.average_score || 0}%</span>
                    </div>
                    <div className="progress-bar"><div className="fill" style={{ width: `${data?.average_score || 0}%` }} /></div>
                  </div>

                  <button className="start-btn" onClick={() => navigate('/ai-portal')}>
                    START SMART REVIEW
                  </button>
                </>
              ) : (
                <div className="focus-empty">
                  <p>Take at least 2 tests for AI Pulse to generate your focus target.</p>
                  <TrendingDown size={32} opacity={0.2} style={{ margin: '1rem 0' }} />
                </div>
              )}
            </div>
          </div>

          {/* Upcoming Sessions */}
          <div className="upcoming-sessions">
             <div className="section-header">
               <h3>Upcoming Sessions</h3>
             </div>
             <div className="timeline">
               <div className="timeline-item">
                 <span className="time">PENDING</span>
                 <div className="session-info">
                   <h4>No sessions scheduled</h4>
                   <p>Check back later for class updates.</p>
                 </div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Performance;
