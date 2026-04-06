import React, { useState, useEffect } from 'react';
import { Search, Bell, User, Plus, Microscope, Brain, Network, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AvailableTestCard from './AvailableTestCard';
import CompletedResultCard from './CompletedResultCard';
import FinalPulseBanner from './FinalPulseBanner';
import GapAnalysisCard from './GapAnalysisCard';
import analyticsService from '../../api/analytics';
import './TestsPortal.css';

const TestsPortal = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchTests = async () => {
      try {
        setLoading(true);
        if (user?.id) {
          const res = await analyticsService.getStudentDashboard(user.id);
          setData(res);
        }
      } catch (err) {
        console.error('Failed to fetch tests:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTests();
  }, [user?.id]);

  const hasData = (data?.recent_tests?.length > 0) || false;

  return (
    <div className="tests-portal-container">
      {/* Header */}
      <header className="portal-header">
        <h1 className="portal-title">Tests Portal</h1>
        <div className="portal-actions">
          <div className="search-container">
            <Search size={18} opacity={0.5} />
            <input type="text" placeholder="Find assessment..." />
          </div>
          <button className="icon-button" onClick={() => navigate('/alerts')}><Bell size={20} /></button>
          <button className="icon-button" onClick={() => navigate('/')}><User size={20} /></button>
        </div>
      </header>

      {loading ? (
        <div className="portal-loading">
          <div className="neon-spinner"></div>
          <p>Compiling Test History...</p>
        </div>
      ) : !hasData ? (
        <div className="portal-empty-state">
          <div className="empty-content">
            <div className="empty-icon-pulse">
              <Brain size={48} color="var(--neon-purple)" />
            </div>
            <h2>Assessments Pending</h2>
            <p>Your current academic cycle has no scheduled tests or previous results available on this portal yet.</p>
            <div className="empty-info-card">
              <Info size={16} />
              <span>Reach out to your faculty to synchronize your offline test marks.</span>
            </div>
            <button className="empty-cta-btn" onClick={() => navigate('/')}>
              PORTAL OVERVIEW
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Available Tests Section */}
          <section className="section-wrapper">
            <div className="section-head">
              <h2>Recent Results</h2>
              <span className="section-tag">{data.total_tests_taken} Total</span>
            </div>
            <div className="results-grid">
              {data.recent_tests.map((test, idx) => (
                <CompletedResultCard 
                  key={idx}
                  title={test.test_title} 
                  date={new Date(test.taken_at).toLocaleDateString()} 
                  score={String(test.score)} 
                  status={test.score >= 40 ? "PASS" : "RE-TAKE"} 
                  iconType={test.score >= 80 ? "star" : "cyan"}
                />
              ))}
            </div>
          </section>

          {/* Footer Section */}
          <footer className="tests-footer">
            <FinalPulseBanner />
            <GapAnalysisCard onClick={() => navigate('/gap-analysis')} />
          </footer>
        </>
      )}

      {/* FAB */}
      <button className="fab-button" title="Request New Test">
        <Plus />
      </button>
    </div>
  );
};

export default TestsPortal;
