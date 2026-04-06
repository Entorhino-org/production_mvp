import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ProficiencyVarianceCard from './ProficiencyVarianceCard';
import DomainConfidenceStats from './DomainConfidenceStats';
import TopicModuleCard from './TopicModuleCard';
import analyticsService from '../../api/analytics';
import { Target, Info, SearchCode } from 'lucide-react';
import './GapAnalysis.css';

const GapAnalysisPortal = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchGapData = async () => {
      try {
        setLoading(true);
        if (user?.id) {
          const res = await analyticsService.getStudentDashboard(user.id);
          setData(res);
        }
      } catch (err) {
        console.error('Failed to fetch gap analysis:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchGapData();
  }, [user?.id]);

  const hasGaps = data && data.total_tests_taken >= 2;

  return (
    <div className="gap-container">
      {/* Header */}
      <header className="gap-header">
        <h1>Gap <span>Analysis</span></h1>
        <p>Identifying the dissonance between your current trajectory and total mastery.</p>
      </header>

      {loading ? (
        <div className="portal-loading">
          <div className="neon-spinner"></div>
          <p>Analyzing Neural Pathways...</p>
        </div>
      ) : !hasGaps ? (
        <div className="portal-empty-state">
           <div className="empty-content">
            <div className="empty-icon-pulse">
              <SearchCode size={48} color="var(--neon-purple)" />
            </div>
            <h2>Initial Assessment Required</h2>
            <p>For an accurate Gap Analysis, your AI tutor needs at least 2 detailed test results to identify your mastery dissonance.</p>
            <div className="empty-info-card">
              <Target size={16} />
              <span>Complete 2 subjects to generate your personalized learning targets.</span>
            </div>
            <button className="empty-cta-btn" onClick={() => navigate('/tests')}>
              COMPLETE ASSESSMENTS
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Top 2-Col Stats */}
          <div className="gap-top-grid">
            <ProficiencyVarianceCard 
              data={data.recent_tests.map(t => ({
                subject: t.test_title.split(':')[0] || 'Subject',
                topic: t.test_title,
                current: t.score,
                target: 90
              }))} 
            />
            <DomainConfidenceStats 
              domains={[
                { label: 'Overall Proficiency', score: data.average_score, color: 'purple' }
              ]} 
              action="Complete specialized subject deep-dive" 
            />
          </div>

          {/* Footer */}
          <footer className="gap-footer">
            <div className="pulse-sync-box">
              <div className="sync-gauge">
                <svg width="50" height="50">
                  <circle cx="25" cy="25" r="22" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
                  <circle cx="25" cy="25" r="22" fill="none" stroke="var(--neon-purple)" strokeWidth="4" strokeDasharray="138" strokeDashoffset={138 - (data.average_score / 100 * 138)} strokeLinecap="round" />
                </svg>
                <span className="sync-pct">{data.average_score}%</span>
              </div>
              <div className="sync-text">
                <b>Total Mastery Sync</b>
                <p>You are {100 - data.average_score}% away from your personalized 'Mastery State'.</p>
              </div>
            </div>

            <div className="gap-footer-actions">
              <button className="btn-gap-neon" disabled={!hasGaps}>Download Gap Report</button>
              <button className="btn-gap-glass">Adjust Target Score</button>
            </div>
          </footer>
        </>
      )}
    </div>
  );
};

export default GapAnalysisPortal;
