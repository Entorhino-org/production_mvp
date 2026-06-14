import React, { useState } from 'react';
import { Search, Moon, Sun, Bell, Settings, ArrowUpRight, Beaker, FunctionSquare, CheckCircle2, UserPlus, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import TeacherSidebar from './TeacherSidebar';
import TeacherTopicsNotes from './TeacherTopicsNotes';
import TeacherAnnouncements from './TeacherAnnouncements';
import TeacherLeaderboard from './TeacherLeaderboard';
import TeacherHomework from './TeacherHomework';
import TeacherAttendance from './TeacherAttendance';
import TeacherInsights from './TeacherInsights';
import TeacherJoinRequests from './TeacherJoinRequests';
import TeacherAlerts from './TeacherAlerts';
import './TeacherDashboard.css';

const TeacherDashboard = () => {
  const [theme, setTheme] = useState('dark');
  const [activePage, setActivePage] = useState('Overview');

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <div className={`teacher-dashboard-wrapper ${theme === 'light' ? 'light-theme' : ''}`}>
      <TeacherSidebar activePage={activePage} onPageChange={setActivePage} />
      
      <div className="td-main">
        {/* Top Header */}
        <header className="td-topbar">
          <div className="td-search">
            <Search size={18} color="var(--td-text-muted)" />
            <input type="text" placeholder="Search curriculum, students, or grades..." />
          </div>
          
          <div className="td-top-actions">
            <button className="td-icon-btn" onClick={toggleTheme} aria-label="Toggle Theme">
              <AnimatePresence mode="wait">
                {theme === 'dark' ? (
                  <motion.div
                    key="moon"
                    initial={{ scale: 0.5, rotate: -90, opacity: 0 }}
                    animate={{ scale: 1, rotate: 0, opacity: 1 }}
                    exit={{ scale: 0.5, rotate: 90, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Moon size={20} />
                  </motion.div>
                ) : (
                  <motion.div
                    key="sun"
                    initial={{ scale: 0.5, rotate: 90, opacity: 0 }}
                    animate={{ scale: 1, rotate: 0, opacity: 1 }}
                    exit={{ scale: 0.5, rotate: -90, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Sun size={20} />
                  </motion.div>
                )}
              </AnimatePresence>
            </button>
            <button className="td-icon-btn" style={{ position: 'relative' }}>
              <Bell size={20} />
              <div style={{ position: 'absolute', top: 0, right: 0, width: 8, height: 8, backgroundColor: '#ef4444', borderRadius: '50%' }} />
            </button>
            <button className="td-icon-btn">
              <Settings size={20} />
            </button>
            <div className="td-top-role">Academic Curator</div>
          </div>
        </header>

        {/* Dashboard Grid */}
        {activePage === 'Overview' && (
          <div className="td-content">
          {/* Left Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Top Row - Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '24px' }}>
              
              {/* Performance Stats */}
              <div className="td-card td-performance-card">
                <div>
                  <div className="td-card-header">
                    <span className="td-card-title">CLASS PERFORMANCE AVERAGE</span>
                    <div className="td-stat-change">
                      <ArrowUpRight size={14} style={{ marginRight: 4 }} />
                      +2.4% vs last term
                    </div>
                  </div>
                  <h3 className="td-stat-big">94.2%</h3>
                </div>
                
                <div className="td-perf-stats">
                  <div className="td-mini-stat">
                    <h5>Active Students</h5>
                    <p>124</p>
                  </div>
                  <div className="td-mini-stat">
                    <h5>Pending Reviews</h5>
                    <p>18</p>
                  </div>
                  <div className="td-mini-stat">
                    <h5>Course Completion</h5>
                    <p>68%</p>
                  </div>
                </div>
              </div>

              {/* Milestone */}
              <div className="td-card td-milestone-card">
                <span className="td-card-title">NEXT MILESTONE</span>
                <h3 className="td-milestone-title">Advanced Calculus Final Submissions</h3>
                
                <div className="td-avatars">
                  <img src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&h=50&fit=crop" className="td-avatar" alt="student" />
                  <img src="https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=50&h=50&fit=crop" className="td-avatar" alt="student" />
                  <img src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=50&h=50&fit=crop" className="td-avatar" alt="student" />
                  <span className="td-avatar-extra">+12 more submitted</span>
                </div>

                <button className="td-btn-secondary">Review Submissions</button>
              </div>
            </div>

            {/* Active Curriculums */}
            <div>
              <div className="td-section-title">
                Active Curriculums
                <span className="td-view-all">View All Schedule</span>
              </div>
              <div className="td-curriculums">
                <div className="td-curr-card biology">
                  <div className="td-curr-header">
                    <div className="td-curr-icon"><Beaker size={20} /></div>
                    <span className="td-semester-badge">SEMESTER A</span>
                  </div>
                  <h4>Molecular Biology 401</h4>
                  <p>32 Students • Mon/Wed/Fri</p>
                </div>
                <div className="td-curr-card quantum">
                  <div className="td-curr-header">
                    <div className="td-curr-icon"><div style={{fontSize: '18px', fontWeight: 'bold'}}>&Sigma;</div></div>
                    <span className="td-semester-badge">SEMESTER B</span>
                  </div>
                  <h4>Quantum Mechanics II</h4>
                  <p>18 Students • Tue/Thu</p>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="td-card" style={{ flex: 1 }}>
              <div className="td-section-title">Recent Activity</div>
              <div className="td-activity-list">
                <div className="td-activity-item">
                  <div className="td-activity-icon td-act-blue"><CheckCircle2 size={16} /></div>
                  <div className="td-activity-content">
                    <h5>Assignment Graded: <span>"Statistical Analysis"</span></h5>
                    <p>Sent to 45 students in Introduction to Data Science</p>
                    <span className="td-activity-time">2 HOURS AGO</span>
                  </div>
                </div>
                
                <div className="td-activity-item">
                  <div className="td-activity-icon td-act-green"><UserPlus size={16} /></div>
                  <div className="td-activity-content">
                    <h5>New Student Enrolled: <span>Sarah Jenkins</span></h5>
                    <p>Added to Advanced Organic Chemistry</p>
                    <span className="td-activity-time">5 HOURS AGO</span>
                  </div>
                </div>

                <div className="td-activity-item">
                  <div className="td-activity-icon td-act-red"><AlertCircle size={16} /></div>
                  <div className="td-activity-content">
                    <h5>Alert: <span>Low engagement detected</span></h5>
                    <p>5 students haven't logged in for over 10 days</p>
                    <span className="td-activity-time">YESTERDAY</span>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* Right Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Calendar */}
            <div className="td-card" style={{ padding: '24px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>October 2023</h4>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="td-icon-btn" style={{ padding: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', width: '24px', height: '24px' }}>&lt;</button>
                  <button className="td-icon-btn" style={{ padding: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', width: '24px', height: '24px' }}>&gt;</button>
                </div>
              </div>

              <div className="td-calendar-grid">
                <div className="td-cal-day-name">S</div>
                <div className="td-cal-day-name">M</div>
                <div className="td-cal-day-name">T</div>
                <div className="td-cal-day-name">W</div>
                <div className="td-cal-day-name">T</div>
                <div className="td-cal-day-name">F</div>
                <div className="td-cal-day-name">S</div>

                <div className="td-cal-day muted">25</div>
                <div className="td-cal-day muted">26</div>
                <div className="td-cal-day muted">27</div>
                <div className="td-cal-day muted">28</div>
                <div className="td-cal-day">1</div>
                <div className="td-cal-day">2</div>
                <div className="td-cal-day">3</div>
                
                <div className="td-cal-day">4</div>
                <div className="td-cal-day">5</div>
                <div className="td-cal-day active">6</div>
                <div className="td-cal-day">7</div>
                <div className="td-cal-day">8</div>
                <div className="td-cal-day">9</div>
                <div className="td-cal-day">10</div>
              </div>
            </div>

            {/* Reminders */}
            <div className="td-card" style={{ flex: 1 }}>
              <div className="td-section-title">
                Reminders
                <span style={{ fontSize: '12px', color: 'var(--td-text-muted)', fontWeight: 'normal' }}>3 Tasks</span>
              </div>
              <div className="td-reminders-list">
                <div className="td-reminder-item td-rem-blue">
                  <CheckCircle2 color="var(--td-accent)" size={16} />
                  <div className="td-reminder-content">
                    <h5>Grade Midterms</h5>
                    <p>Biology 401</p>
                  </div>
                </div>

                <div className="td-reminder-item td-rem-green">
                  <div style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid var(--td-green)' }} />
                  <div className="td-reminder-content">
                    <h5>Department Sync</h5>
                    <p>3:00 PM Today</p>
                  </div>
                </div>

                <div className="td-reminder-item td-rem-red">
                  <div style={{ width: 16, height: 12, backgroundColor: 'var(--td-red)', borderRadius: '2px' }} />
                  <div className="td-reminder-content">
                    <h5>Parent Liaison</h5>
                    <p>Urgent Request</p>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
        )}
        {activePage === 'Topics / Notes' && (
          <div className="td-content" style={{ display: 'block', padding: '0' }}>
            <TeacherTopicsNotes />
          </div>
        )}
        {activePage === 'Announcements' && (
          <div className="td-content" style={{ display: 'block', padding: '0', background: 'transparent', border: 'none' }}>
            <TeacherAnnouncements />
          </div>
        )}
        {activePage === 'Leaderboard' && (
          <div className="td-content" style={{ display: 'block', padding: '0', background: 'transparent', border: 'none' }}>
            <TeacherLeaderboard />
          </div>
        )}
        {activePage === 'Homework' && (
          <div className="td-content" style={{ display: 'block', padding: '0', background: 'transparent', border: 'none' }}>
            <TeacherHomework />
          </div>
        )}
        {activePage === 'Attendance' && (
          <div className="td-content" style={{ display: 'block', padding: '0', background: 'transparent', border: 'none' }}>
            <TeacherAttendance />
          </div>
        )}
        {activePage === 'Class Insights' && (
          <div className="td-content" style={{ display: 'block', padding: '0', background: 'transparent', border: 'none' }}>
            <TeacherInsights />
          </div>
        )}
        {activePage === 'Join Requests' && (
          <div className="td-content" style={{ display: 'block', padding: '0', background: 'transparent', border: 'none' }}>
            <TeacherJoinRequests />
          </div>
        )}
        {activePage === 'Alerts' && (
          <div className="td-content" style={{ display: 'block', padding: '0', background: 'transparent', border: 'none' }}>
            <TeacherAlerts />
          </div>
        )}
      </div>
    </div>
  );
};

export default TeacherDashboard;
