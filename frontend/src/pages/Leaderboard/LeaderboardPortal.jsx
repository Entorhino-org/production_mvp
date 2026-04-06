import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import TopPodiumCard from './TopPodiumCard';
import RankTable from './RankTable';
import PulsePredictionBanner from './PulsePredictionBanner';
import analyticsService from '../../api/analytics';
import { Trophy, TrendingUp, Info } from 'lucide-react';
import './Leaderboard.css';

const LeaderboardPortal = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState([]);
  const navigate = useNavigate();
  const firstName = user?.full_name?.split(' ')[0] || 'Scholar';

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        setLoading(true);
        const res = await analyticsService.getLeaderboard();
        setData(res || []);
      } catch (err) {
        console.error('Failed to fetch leaderboard:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  const topThree = data.slice(0, 3).map((s, idx) => ({
    rank: idx + 1,
    name: s.full_name,
    subject: s.role || 'Scholar',
    xp: s.xp || 0,
    avatar: `https://ui-avatars.com/api/?name=${s.full_name}&background=A855F7&color=fff`,
    badge: idx === 0 ? 'ELITE CHAMPION' : idx === 1 ? 'RUNNER UP' : 'THE SPECIALIST',
    type: idx === 0 ? 'champion' : idx === 1 ? 'runner' : 'special'
  }));

  const others = data.slice(3).map((s, idx) => ({
    rank: idx + 4,
    name: s.full_name,
    subject: s.role || 'Scholar',
    efficiency: 0,
    momentum: 'flat',
    score: s.xp || 0,
    avatar: `https://ui-avatars.com/api/?name=${s.full_name}&background=A855F7&color=fff`,
    isUser: s.id === user?.id
  }));

  return (
    <div className="lb-container">
      {/* Header Row */}
      <header className="lb-header-row">
        <div className="lb-title-box">
          <h1>Hall of <span>Velocity</span></h1>
          <p>Real-time performance rankings across the entire cohort. Your effort defines your peak.</p>
        </div>
      </header>

      {loading ? (
        <div className="portal-loading">
          <div className="neon-spinner"></div>
          <p>Analyzing Global Rankings...</p>
        </div>
      ) : data.length === 0 ? (
        <div className="portal-empty-state">
           <div className="empty-content">
            <div className="empty-icon-pulse">
              <Trophy size={48} color="var(--neon-purple)" />
            </div>
            <h2>Arena Awaits</h2>
            <p>The leaderboard is currently empty for this academic cycle. Be the first to secure a top spot by completing your first assessment!</p>
            <div className="empty-info-card">
              <TrendingUp size={16} />
              <span>Participate in school-wide challenges to earn XP and climb the ranks.</span>
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
          <RankTable students={others} />

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
