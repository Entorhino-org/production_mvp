import React, { useState } from 'react';
import { 
  FileUp, 
  Lightbulb, 
  ChevronDown, 
  Camera, 
  Image as ImageIcon 
} from 'lucide-react';
import './TeacherHomework.css';

const TeacherHomework = () => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [section, setSection] = useState('Select Section');
  const [subject, setSubject] = useState('Mathematics');
  const [chapter, setChapter] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [dueTime, setDueTime] = useState('');
  const [submissionType, setSubmissionType] = useState('DIGITAL PDF');

  return (
    <div className="th-container">
      {/* Header Area */}
      <div className="th-header-wrapper">
        <div className="th-header-left">
          <span className="th-super-title">TASK MANAGEMENT</span>
          <h2 className="th-title">Assign Homework</h2>
          <p className="th-subtitle">Curate and distribute new academic tasks to your selected sections</p>
        </div>
        
        <div className="th-header-actions">
          <button className="th-btn-secondary">Save Draft</button>
          <button className="th-btn-primary">Publish Assignment</button>
        </div>
      </div>

      <div className="th-content-grid">
        
        {/* Left Column */}
        <div className="th-main-col">
          
          {/* General Details Box */}
          <div className="th-box th-box-border-blue">
            <h3 className="th-box-title">General Details</h3>
            
            <div className="th-form-group">
              <label>HOMEWORK TITLE</label>
              <input 
                type="text" 
                placeholder="e.g. Advanced Calculus: Integrals of Transcendental Functions" 
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            
            <div className="th-form-group">
              <label>INSTRUCTIONAL DESCRIPTION</label>
              <textarea 
                placeholder="Provide detailed instructions, learning objectives, and reference materials..."
                rows={5}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              ></textarea>
            </div>
          </div>

          {/* Upload Materials Box */}
          <div className="th-upload-box">
            <div className="th-upload-icon-wrapper">
              <FileUp size={24} color="var(--td-blue)" />
            </div>
            <h4 className="th-upload-title">Upload Reference Materials</h4>
            <p className="th-upload-desc">Drag and drop diagrams, chapter PDFs, or worksheets here. Max size: 25MB.</p>
            <button className="th-upload-btn">Select Files</button>
          </div>

          {/* Recommended Reference Images */}
          <div className="th-reference-section">
            <h4 className="th-ref-title">Recommended Reference Images</h4>
            <div className="th-ref-grid">
              <div className="th-ref-card">
                <img src="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=300&h=200&fit=crop" alt="Quantum Physics"/>
                <div className="th-ref-label">QUANTUM PHYSICS</div>
              </div>
              <div className="th-ref-card">
                <img src="https://images.unsplash.com/photo-1632516643763-7eb662d59265?w=300&h=200&fit=crop" alt="Mathematics"/>
                <div className="th-ref-label">MATHEMATICS</div>
              </div>
              <div className="th-ref-card">
                <img src="https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=300&h=200&fit=crop" alt="Chemistry"/>
                <div className="th-ref-label">CHEMISTRY</div>
              </div>
              <div className="th-ref-card th-ref-custom">
                <Camera size={24} color="var(--td-text-muted)" />
                <span>ADD CUSTOM</span>
              </div>
            </div>
          </div>

        </div>

        {/* Right Column */}
        <div className="th-side-col">
          
          {/* Classification Box */}
          <div className="th-box th-box-border-green">
            <h3 className="th-box-title">Classification</h3>
            
            <div className="th-form-group">
              <label>ACADEMIC SECTION</label>
              <div className="th-select-wrapper">
                <select value={section} onChange={(e) => setSection(e.target.value)}>
                  <option>Select Section</option>
                  <option>Grade 12-A</option>
                  <option>Grade 11-B</option>
                </select>
                <ChevronDown size={14} className="th-select-icon" />
              </div>
            </div>

            <div className="th-form-group">
              <label>SUBJECT</label>
              <div className="th-select-wrapper">
                <select value={subject} onChange={(e) => setSubject(e.target.value)}>
                  <option>Mathematics</option>
                  <option>Physics</option>
                  <option>Chemistry</option>
                </select>
                <ChevronDown size={14} className="th-select-icon" />
              </div>
            </div>

            <div className="th-form-group">
              <label>CHAPTER / MODULE</label>
              <input 
                type="text" 
                placeholder="e.g. Chapter 04: Thermodynamics"
                value={chapter}
                onChange={(e) => setChapter(e.target.value)}
              />
            </div>
          </div>

          {/* Deadline & Submission Box */}
          <div className="th-box th-box-border-red">
            <h3 className="th-box-title">Deadline & Submission</h3>
            
            <div className="th-form-row">
              <div className="th-form-group">
                <label>DUE DATE</label>
                <input 
                  type="date" 
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                />
              </div>
              <div className="th-form-group">
                <label>DUE TIME</label>
                <input 
                  type="time" 
                  value={dueTime}
                  onChange={(e) => setDueTime(e.target.value)}
                />
              </div>
            </div>

            <div className="th-form-group th-submission-group">
              <label>SUBMISSION TYPE</label>
              <div className="th-pill-group">
                {['DIGITAL PDF', 'HANDWRITTEN', 'CODE REPOSITORY'].map(type => (
                  <button 
                    key={type}
                    className={`th-pill-btn ${submissionType === type ? 'active' : ''}`}
                    onClick={() => setSubmissionType(type)}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Pro-Tip Box */}
          <div className="th-tip-box">
            <Lightbulb size={20} color="var(--td-blue)" className="th-tip-icon" />
            <h4>Pro-Tip</h4>
            <p>Homework assigned before 10 AM on weekdays typically sees a 45% higher timely submission rate.</p>
          </div>

        </div>
      </div>
    </div>
  );
};

export default TeacherHomework;
