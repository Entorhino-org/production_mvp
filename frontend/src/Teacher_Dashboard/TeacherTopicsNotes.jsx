import React, { useState } from 'react';
import { 
  Folder, 
  FileText, 
  Upload, 
  MoreVertical, 
  Plus, 
  Clock, 
  Share2, 
  Download, 
  Filter,
  Search,
  Video,
  FileAudio
} from 'lucide-react';
import './TeacherTopicsNotes.css';

const TeacherTopicsNotes = () => {
  const [activeTab, setActiveTab] = useState('folders');

  const folders = [
    { id: 1, name: 'Molecular Biology 401', files: 42, color: 'var(--td-blue)' },
    { id: 2, name: 'Quantum Mechanics II', files: 28, color: 'var(--td-accent)' },
    { id: 3, name: 'Data Science Intro', files: 56, color: 'var(--td-green)' },
    { id: 4, name: 'General Resources', files: 12, color: 'var(--td-text-muted)' },
  ];

  const recentNotes = [
    { id: 1, name: 'Lecture 12: Cellular Replication.pdf', type: 'pdf', course: 'Molecular Biology 401', size: '2.4 MB', date: '2 hours ago' },
    { id: 2, name: 'Wave Function Exercises.docx', type: 'doc', course: 'Quantum Mechanics II', size: '1.1 MB', date: 'Yesterday' },
    { id: 3, name: 'Statistical Testing Models.xlsx', type: 'sheet', course: 'Data Science Intro', size: '3.8 MB', date: 'Oct 4, 2023' },
    { id: 4, name: 'Introductory Lab Video.mp4', type: 'video', course: 'General Resources', size: '124 MB', date: 'Oct 1, 2023' },
  ];

  const getIconForType = (type) => {
    switch(type) {
      case 'video': return <Video size={20} className="file-icon video" />;
      case 'audio': return <FileAudio size={20} className="file-icon audio" />;
      default: return <FileText size={20} className="file-icon doc" />;
    }
  };

  return (
    <div className="tn-container">
      {/* Top Action Bar */}
      <div className="tn-header">
        <div className="tn-header-left">
          <h2 className="tn-title">Topics & Notes</h2>
          <p className="tn-subtitle">Manage curriculum resources, upload materials, and share with your classes.</p>
        </div>
        <div className="tn-header-actions">
          <button className="tn-btn-primary">
            <Upload size={18} />
            Upload File
          </button>
          <button className="tn-btn-secondary">
            <Plus size={18} />
            New Folder
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="tn-content-grid">
        
        {/* Left Column: Folders & Files */}
        <div className="tn-main-col">
          
          <div className="tn-tabs">
            <div 
              className={`tn-tab ${activeTab === 'folders' ? 'active' : ''}`}
              onClick={() => setActiveTab('folders')}
            >
              Curriculum Folders
            </div>
            <div 
              className={`tn-tab ${activeTab === 'shared' ? 'active' : ''}`}
              onClick={() => setActiveTab('shared')}
            >
              Shared with Me
            </div>
            <div 
              className={`tn-tab ${activeTab === 'archived' ? 'active' : ''}`}
              onClick={() => setActiveTab('archived')}
            >
              Archive
            </div>
          </div>

          {/* Quick Filters */}
          <div className="tn-filters">
            <div className="tn-search-bar">
              <Search size={16} color="var(--td-text-muted)" />
              <input type="text" placeholder="Search files, folders, topics..." />
            </div>
            <button className="tn-icon-btn"><Filter size={18} /> Filter</button>
          </div>

          {/* Folders Grid */}
          {activeTab === 'folders' && (
            <div className="tn-section">
              <h3 className="tn-section-title">My Folders</h3>
              <div className="tn-folders-grid">
                {folders.map(folder => (
                  <div key={folder.id} className="tn-folder-card">
                    <div className="tn-folder-icon" style={{ color: folder.color }}>
                      <Folder size={32} fill="currentColor" fillOpacity={0.2} />
                    </div>
                    <div className="tn-folder-info">
                      <h4>{folder.name}</h4>
                      <p>{folder.files} files</p>
                    </div>
                    <button className="tn-more-btn"><MoreVertical size={16} /></button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Files List */}
          <div className="tn-section" style={{ marginTop: '32px' }}>
            <h3 className="tn-section-title">Recent Uploads</h3>
            <div className="tn-files-list">
              <div className="tn-file-header">
                <div className="tn-col-name">Name</div>
                <div className="tn-col-course">Course</div>
                <div className="tn-col-size">Size</div>
                <div className="tn-col-date">Date Modified</div>
                <div className="tn-col-actions"></div>
              </div>

              {recentNotes.map(file => (
                <div key={file.id} className="tn-file-row">
                  <div className="tn-col-name">
                    {getIconForType(file.type)}
                    <span>{file.name}</span>
                  </div>
                  <div className="tn-col-course">
                    <span className="tn-badge">{file.course}</span>
                  </div>
                  <div className="tn-col-size">{file.size}</div>
                  <div className="tn-col-date">{file.date}</div>
                  <div className="tn-col-actions">
                    <button className="tn-action-icon"><Share2 size={16} /></button>
                    <button className="tn-action-icon"><Download size={16} /></button>
                    <button className="tn-action-icon"><MoreVertical size={16} /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Column: Storage & Quick Stats */}
        <div className="tn-side-col">
          
          {/* Storage Snapshot */}
          <div className="tn-side-card">
            <h3>Storage Overview</h3>
            <div className="tn-storage-chart">
              <div className="tn-storage-bar">
                <div className="tn-storage-used doc" style={{ width: '45%' }}></div>
                <div className="tn-storage-used video" style={{ width: '25%' }}></div>
                <div className="tn-storage-used other" style={{ width: '10%' }}></div>
              </div>
            </div>
            <div className="tn-storage-details">
              <span>8.4 GB Used</span>
              <span>15 GB Total</span>
            </div>
            
            <div className="tn-storage-legend">
              <div className="tn-legend-item">
                <div className="tn-dot doc"></div>
                <span>Documents (4.2 GB)</span>
              </div>
              <div className="tn-legend-item">
                <div className="tn-dot video"></div>
                <span>Videos (2.8 GB)</span>
              </div>
              <div className="tn-legend-item">
                <div className="tn-dot other"></div>
                <span>Other (1.4 GB)</span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="tn-side-card">
            <h3>Suggested Actions</h3>
            <div className="tn-suggested-actions">
              <button className="tn-suggested-btn">
                <div className="btn-icon"><Share2 size={16}/></div>
                <div className="btn-text">
                  <h4>Share Curriculum</h4>
                  <p>Send folder links to new students</p>
                </div>
              </button>
              <button className="tn-suggested-btn">
                <div className="btn-icon"><Clock size={16}/></div>
                <div className="btn-text">
                  <h4>Review Pending</h4>
                  <p>3 Student submissions to check</p>
                </div>
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default TeacherTopicsNotes;
