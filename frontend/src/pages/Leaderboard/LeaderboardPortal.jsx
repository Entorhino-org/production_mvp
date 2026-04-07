import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import TopPodiumCard from './TopPodiumCard';
import RankTable from './RankTable';
import PulsePredictionBanner from './PulsePredictionBanner';
import analyticsService from '../../api/analytics';
import { Trophy, TrendingUp, Info, Activity, BookOpen, Calendar } from 'lucide-react';
import './Leaderboard.css';

const LeaderboardPortal = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [allData, setAllData] = useState({
    by_attendance: [],
    by_test_score: [],
    by_homework_score: []
  });
  const [activeCategory, setActiveCategory] = useState('by_test_score');
  
  const navigate = useNavigate();
  const firstName = user?.full_name?.split(' ')[0] || 'Scholar';

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        setLoading(true);
        const res = await analyticsService.getLeaderboard();
        
        // Robust update: handle both array (legacy) and object (v1) formats
        if (res && typeof res === 'object' && !Array.isArray(res)) {
          setAllData({
            by_attendance: res.by_attendance || [],
            by_test_score: res.by_test_score || [],
            by_homework_score: res.by_homework_score || []
          });
        } else if (Array.isArray(res)) {
          setAllData({
            by_attendance: [],
            by_test_score: res || [],
            by_homework_score: []
          });
        }
      } catch (err) {
        console.error('Failed to fetch leaderboard:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  const currentData = useMemo(() => {
    const data = allData[activeCategory] || [];
    return Array.isArray(data) ? data : [];
  }, [allData, activeCategory]);

  const topThree = useMemo(() => {
    return currentData.slice(0, 3).map((s, idx) => ({
      rank: idx + 1,
      name: s.full_name || s.name || 'Scholar',
      subject: s.class_name || s.role || 'Scholar',
      xp: s.avg_test_score || s.attendance_rate || s.avg_homework_score || 0,
      avatar: `https://ui-avatars.com/api/?name=${s.full_name || s.name || 'S'}&background=A855F7&color=fff`,
      badge: idx === 0 ? 'ELITE CHAMPION' : idx === 1 ? 'RUNNER UP' : 'THE SPECIALIST',
      type: idx === 0 ? 'champion' : idx === 1 ? 'runner' : 'special'
    }));
  }, [currentData]);

  const others = useMemo(() => {
    return currentData.slice(3).map((s, idx) => ({
      rank: idx + 4,
      name: s.full_name || s.name || 'Scholar',
      subject: s.class_name || s.role || 'Scholar',
      efficiency: 0,
      momentum: 'flat',
      score: s.avg_test_score || s.attendance_rate || s.avg_homework_score || 0,
      avatar: `https://ui-avatars.com/api/?name=${s.full_name || s.name || 'S'}&background=A855F7&color=fff`,
      isUser: s.id === user?.id
    }));
  }, [currentData, user?.id]);

  const categoryLabel = activeCategory === 'by_test_score' ? 'Test Performance' : 
                        activeCategory === 'by_attendance' ? 'Attendance Rate' : 'Homework Mastery';

  return (
    <div className="lb-container">
      {/* Header Row */}
      <header className="lb-header-row">
        <div className="lb-title-box">
          <h1>Hall of <span>Velocity</span></h1>
          <p>Real-time performance rankings across the entire cohort. Your effort defines your peak.</p>
        </div>

        {/* Global Stats Tabs */}
        {!loading && (
          <div className="lb-category-tabs">
            <button 
              className={`cat-tab ${activeCategory === 'by_test_score' ? 'active' : ''}`}
              onClick={() => setActiveCategory('by_test_score')}
            >
              <Activity size={14} /> Tests
            </button>
            <button 
              className={`cat-tab ${activeCategory === 'by_attendance' ? 'active' : ''}`}
              onClick={() => setActiveCategory('by_attendance')}
            >
              <Calendar size={14} /> Attendance
            </button>
            <button 
              className={`cat-tab ${activeCategory === 'by_homework_score' ? 'active' : ''}`}
              onClick={() => setActiveCategory('by_homework_score')}
            >
              <BookOpen size={14} /> Homework
            </button>
          </div>
        )}
      </header>

      {loading ? (
        <div className="portal-loading">
          <div className="neon-spinner"></div>
          <p>Analyzing Global {categoryLabel}...</p>
        </div>
      ) : currentData.length === 0 ? (
        <div className="portal-empty-state">
           <div className="empty-content">
            <div className="empty-icon-pulse">
              <Trophy size={48} color="var(--neon-purple)" />
            </div>
            <h2>Arena Awaits</h2>
            <p>The {categoryLabel} leaderboard is currently empty for this academic cycle.</p>
            <div className="empty-info-card">
              <TrendingUp size={16} />
              <span>Participate in activities to earn your spot on the leaderboard.</span>
            </div>
            <button className="empty-cta-btn" onClick={() => navigate('/tests')}>
              EARN XP NOW
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Podium Top 3 */}
          <section className="lb-podium">
            {topThree.map((p, idx) => <TopPodiumCard key={idx} {...p} />)}
          </section>

          {/* Other Rankings List */}
          <RankTable students={others} categoryLabel={categoryLabel} />

          {/* Pulse Banner */}
          <PulsePredictionBanner 
            name={firstName} 
            prediction="the race has just begun! Consistency in your next few tests will determine your first baseline rank. Target the Top 10 to unlock exclusive rewards."
            onAction={() => navigate('/gap-analysis')}
          />
        </>
      )}
    </div>
  );
};

export default LeaderboardPortal;

