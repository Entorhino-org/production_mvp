import React, { useState, useEffect } from 'react';
import { MessageSquareText, Bell, Megaphone, Info } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import FeaturedUpdateCard from './FeaturedUpdateCard';
import WeeklyPulseCard from './WeeklyPulseCard';
import UpdateGridItem from './UpdateGridItem';
import CtaBanner from './CtaBanner';
import communicationService from '../../api/communication';
import './Announcements.css';

const AnnouncementsPage = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [announcements, setAnnouncements] = useState([]);
  const [systemAlerts, setSystemAlerts] = useState([]);
  const [activeTab, setActiveTab] = useState('ALL');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [annRes, alertRes] = await Promise.all([
          communicationService.getAnnouncements(),
          communicationService.getAlerts()
        ]);
        setAnnouncements(annRes || []);
        setSystemAlerts(alertRes || []);
      } catch (err) {
        console.error('Failed to fetch communications:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await communicationService.markAllRead();
      setAnnouncements(announcements.map(a => ({ ...a, is_read: true })));
      setSystemAlerts(systemAlerts.map(a => ({ ...a, is_read: true })));
    } catch (err) {
      console.log('Failed to mark all read:', err);
    }
  };

  const allUpdates = [
    ...announcements.map(a => ({
      id: a.id,
      title: a.title,
      type: 'megaphone',
      rawDate: a.created_at,
      date: a.created_at ? new Date(a.created_at).toLocaleDateString() : 'RECENT',
      desc: a.content,
      cta: 'Read More',
      category: 'CAMPUS',
      isRead: a.is_read
    })),
    ...systemAlerts.map(a => ({
      id: a.id,
      title: a.alert_type ? a.alert_type.replace(/_/g, ' ') : 'System Alert',
      type: 'bell',
      rawDate: a.created_at,
      date: a.created_at ? new Date(a.created_at).toLocaleDateString() : 'RECENT',
      desc: a.message,
      cta: 'Action Required',
      category: 'ACADEMIC',
      isRead: a.is_read
    }))
  ].sort((a, b) => {
    if (!a.rawDate) return 1;
    if (!b.rawDate) return -1;
    return new Date(b.rawDate) - new Date(a.rawDate);
  });

  const filteredUpdates = allUpdates.filter(upd => 
    activeTab === 'ALL' || upd.category === activeTab
  );

  return (
    <div className="ann-container">
      {/* Header */}
      <header className="ann-header">
        <div className="header-lhs">
          <h1>Announcements</h1>
          <p>Syncing institutional news and smart system alerts in real-time.</p>
        </div>
        <div className="header-rhs">
           <button className="mark-read-btn" onClick={handleMarkAllRead}>
             MARK ALL AS READ
           </button>
           <div className="user-avatar-mini" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
              <img src={`https://ui-avatars.com/api/?name=${user?.full_name || 'User'}&background=A855F7&color=fff`} alt="User" />
           </div>
        </div>
      </header>

      {/* Featured Row */}
      <div className="ann-top-row">
        <FeaturedUpdateCard 
          badge={announcements.length > 0 ? "LATEST" : "SYSTEM CHANNEL"}
          title={announcements[0]?.title || "Campus Ecosystem Active"}
          desc={announcements[0]?.content || "The Entorhino communication channel is now live. All academic updates, holiday schedules, and event registrations will be broadcast here for real-time tracking."}
          date={announcements[0]?.created_at ? new Date(announcements[0].created_at).toLocaleDateString() : "ACTIVE NOW"}
        />
        <WeeklyPulseCard 
          events={announcements.length} 
          resources={systemAlerts.filter(a => !a.is_read).length} 
          deadline="Stay updated, stay ahead." 
        />
      </div>

      {/* Recent Updates Grid */}
      <section className="recent-section">
        <div className="recent-header">
          <h2>Updates Vault</h2>
          <div className="filter-group">
            {['ALL', 'CAMPUS', 'ACADEMIC'].map(cat => (
              <button 
                key={cat}
                className={`filter-btn ${activeTab === cat ? 'active' : ''}`}
                onClick={() => setActiveTab(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
        
        {loading ? (
          <div className="portal-loading">
            <div className="neon-spinner"></div>
            <p>Gathering Intelligence...</p>
          </div>
        ) : filteredUpdates.length > 0 ? (
          <div className="recent-grid">
            {filteredUpdates.map((upd, idx) => (
              <UpdateGridItem 
                key={upd.id || idx} 
                {...upd} 
                icon={upd.type === 'bell' ? <Bell size={18} /> : <Megaphone size={18} />}
              />
            ))}
          </div>
        ) : (
          <div className="portal-empty-state">
             <div className="empty-content">
              <div className="empty-icon-pulse">
                <Info size={48} color="var(--neon-purple)" />
              </div>
              <h2>No New Updates</h2>
              <p>Your announcements vault is currently clear. Any school news or smart alerts will instantly appear here.</p>
            </div>
          </div>
        )}
      </section>

      {/* Bottom CTA */}
      <CtaBanner />

      {/* Fixed Chat FAB */}
      <div className="fab-msg">
        <MessageSquareText size={20} />
      </div>
    </div>
  );
};

export default AnnouncementsPage;
