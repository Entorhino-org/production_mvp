import React, { useState, useEffect } from 'react';
import { Search, Bell, Filter, Download, Calendar as CalendarIcon, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import MonthlyAverageGauge from './MonthlyAverageGauge';
import TrendAnalysisChart from './TrendAnalysisChart';
import AttendanceHistoryFeed from './AttendanceHistoryFeed';
import SubjectAttendanceBreakdown from './SubjectAttendanceBreakdown';
import ProTipMilestoneCard from './ProTipMilestoneCard';
import AttendanceCalendarView from './AttendanceCalendarView';
import analyticsService from '../../api/analytics';
import './AttendancePortal.css';

const AttendancePortal = ({ user }) => {
  const [showCalendar, setShowCalendar] = useState(false);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAttendance = async () => {
      try {
        setLoading(true);
        if (user?.id) {
          const res = await analyticsService.getStudentDashboard(user.id);
          setData(res);
        }
      } catch (err) {
        console.error('Failed to fetch attendance:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAttendance();
  }, [user?.id]);

  const hasData = data && data.attendance_total > 0;

  return (
    <div className="attendance-container">
      {showCalendar && <AttendanceCalendarView onClose={() => setShowCalendar(false)} />}
      
      {/* Header Row */}
      <header className="att-header">
        <div className="search-insights">
          <Search size={14} opacity={0.5} />
          <input type="text" placeholder="Search sessions..." />
        </div>
        <div className="att-user-profile">
          <div style={{ position: 'relative', cursor: 'pointer' }} onClick={() => navigate('/alerts')}>
            <Bell size={18} opacity={0.6} />
            <div style={{ position: 'absolute', top: -2, right: -2, width: 6, height: 6, background: 'var(--neon-purple)', borderRadius: '50%' }} />
          </div>
          <div className="att-user-text" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
            <span className="att-user-name">{user?.full_name || 'Student'}</span>
            <span className="att-user-sub">{user?.role || 'User'}</span>
          </div>
          <img 
            src={`https://ui-avatars.com/api/?name=${user?.full_name || 'User'}&background=A855F7&color=fff`} 
            alt="profile" 
            style={{ width: '32px', height: '32px', borderRadius: '50%', border: '1px solid var(--neon-purple)', cursor: 'pointer' }}
            onClick={() => navigate('/')}
          />
        </div>
      </header>

      {/* Hero Row */}
      <div className="att-hero">
        <div className="att-hero-text">
          <h1>My <span>Attendance</span></h1>
          <p>Real-time tracking for the current Academic Cycle</p>
        </div>
        <div className="att-hero-actions">
          <button className="btn-filter"><Filter size={14} /> This Month</button>
          <button className="btn-report" disabled={!hasData}><Download size={14} /> Report</button>
        </div>
      </div>

      {!hasData && !loading ? (
        <div className="portal-empty-state">
          <div className="empty-content">
            <div className="empty-icon-pulse">
              <CalendarIcon size={48} color="var(--neon-purple)" />
            </div>
            <h2>No Attendance Records Found</h2>
            <p>Your daily attendance will appear here once sessions begin or records are synced from your classroom.</p>
            <div className="empty-info-card">
              <Info size={16} />
              <span>Contact your class teacher if you believe this is an error.</span>
            </div>
            <button className="empty-cta-btn" onClick={() => navigate('/')}>
              BACK TO DASHBOARD
            </button>
          </div>
        </div>
      ) : loading ? (
        <div className="portal-loading">
          <div className="neon-spinner"></div>
          <p>Syncing Attendance Vault...</p>
        </div>
      ) : (
        <>
          {/* Top 3-Col Stats */}
          <div className="att-top-row">
            <MonthlyAverageGauge 
              pct={data.attendance_rate} 
              present={data.attendance_present} 
              absent={data.attendance_total - data.attendance_present} 
              leave={0} 
            />
            <TrendAnalysisChart 
              data={[0, 0, 0, 0, 0, data.attendance_rate]} 
              diff={0} 
              summary={`Your attendance is currently <b>${data.attendance_rate}%</b>.`}
            />
            <AttendanceHistoryFeed 
              onViewAll={() => setShowCalendar(true)}
              history={[]} // Backend doesn't provide detailed history list yet in performance endpoint
            />
          </div>

          {/* Bottom 2-Col Details */}
          <div className="att-bottom-row">
            <SubjectAttendanceBreakdown subjects={[]} />
            <ProTipMilestoneCard />
          </div>
        </>
      )}
    </div>
  );
};

export default AttendancePortal;
