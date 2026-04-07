import React, { useState } from 'react';
import { Mail, Lock, User, Phone, BookOpen, Heart, UserCheck, AlertCircle, ShieldCheck, LogIn } from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import logo from '../../assets/logo.png';
import authService from '../../api/auth';
import './Auth.css';

const Register = ({ onRegisterSuccess }) => {
  const [role, setRole] = useState('student');
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    confirm_password: '', 
    phone: '',
    subjects: [],
    relationship_type: ''
  });
  const [isOtpStage, setIsOtpStage] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubjectChange = (e) => {
    const subjects = e.target.value.split(',').map(s => s.trim());
    setFormData({ ...formData, subjects });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match.');
      setLoading(false);
      return;
    }

    try {
      const response = await authService.register({ ...formData, role });
      console.log('Registration Step 1 Success:', response);
      setIsOtpStage(true);
    } catch (err) {
      if (!err.response) {
        setError('Cannot connect to server. Please check if the backend is running.');
      } else {
        const detail = err.response.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Registration failed. Check your email/phone format.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const data = await authService.verifyOtp(formData.email, otpCode);
      console.log('Verification successful:', data);
      
      const { access_token, refresh_token, user } = data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      onRegisterSuccess(user);
    } catch (err) {
      if (!err.response) {
        setError('Connection lost. Please try again.');
      } else {
        const detail = err.response.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Invalid OTP code.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-bg-glow glow-1"></div>
      <div className="auth-bg-glow glow-2"></div>
      
      <div className="auth-container">
        <div className="auth-header">
          <img src={logo} alt="ENTORHINO" className="brand-logo-img" />
          <h2>{isOtpStage ? 'Verify Email' : 'Create New ID'}</h2>
          <p>{isOtpStage ? `We sent a code to ${formData.email}` : 'Join the next generation of adaptive learning'}</p>
        </div>

        {error && (
          <div className="error-message">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {!isOtpStage ? (
          <>
            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label className="form-label">Select Your Portal</label>
              <div className="input-container">
                <UserCheck className="input-icon" size={18} />
                <select 
                  className="auth-input role-dropdown"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  required
                >
                  <option value="student">Student Portal</option>
                  <option value="teacher">Teacher Portal</option>
                  <option value="parent">Parent Portal</option>
                </select>
              </div>
            </div>

            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '0.4rem' }}>
                <label className="form-label">Full Name</label>
                <div className="input-container">
                  <User className="input-icon" size={18} />
                  <input 
                    name="full_name"
                    type="text" 
                    className="auth-input" 
                    placeholder="Alex Sterling"
                    value={formData.full_name}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>

              <div className="form-grid-layout" style={{ gap: '0.8rem 1.5rem' }}>
                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <div className="input-container">
                    <Mail className="input-icon" size={18} />
                    <input 
                      name="email"
                      type="email" 
                      className="auth-input" 
                      placeholder="Enter your mail"
                      value={formData.email}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Phone Number</label>
                  <div className="input-container">
                    <Phone className="input-icon" size={18} />
                    <input 
                      name="phone"
                      type="tel" 
                      className="auth-input" 
                      placeholder="Number"
                      value={formData.phone}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Password</label>
                  <div className="input-container">
                    <Lock className="input-icon" size={18} />
                    <input 
                      name="password"
                      type="password" 
                      className="auth-input" 
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Confirm Password</label>
                  <div className="input-container">
                    <Lock className="input-icon" size={18} />
                    <input 
                      name="confirm_password"
                      type="password" 
                      className="auth-input" 
                      placeholder="••••••••"
                      value={formData.confirm_password}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>

              {role !== 'student' && (
                <div className="form-group" style={{ marginTop: '0.4rem' }}>
                  {role === 'teacher' ? (
                    <>
                      <label className="form-label">Subjects (Comma separated)</label>
                      <div className="input-container">
                        <BookOpen className="input-icon" size={18} />
                        <input 
                          name="subjects"
                          type="text" 
                          className="auth-input" 
                          placeholder="Physics, Math, Bio"
                          onChange={handleSubjectChange}
                          required
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <label className="form-label">Relationship to Student</label>
                      <div className="input-container">
                        <Heart className="input-icon" size={18} />
                        <select 
                          name="relationship_type"
                          className="auth-input" 
                          style={{ appearance: 'none' }}
                          value={formData.relationship_type}
                          onChange={handleChange}
                          required
                        >
                          <option value="" disabled>Select relation</option>
                          <option value="father">Father</option>
                          <option value="mother">Mother</option>
                          <option value="guardian">Guardian</option>
                        </select>
                      </div>
                    </>
                  )}
                </div>
              )}

              <button type="submit" className="auth-submit" disabled={loading} style={{ marginTop: '1rem' }}>
                {loading ? (
                  <div className="loading-spinner"></div>
                ) : (
                  <>
                    <UserCheck size={18} />
                    <span>Create My Account</span>
                  </>
                )}
              </button>
            </form>
          </>
        ) : (
          <form className="auth-form" onSubmit={handleVerifyOtp}>
            <div className="form-group">
              <label className="form-label">Validation Code</label>
              <div className="input-container">
                <ShieldCheck className="input-icon" size={18} />
                <input 
                  type="text" 
                  className="auth-input" 
                  placeholder="Enter 6-digit OTP"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  maxLength={6}
                  required
                  autoFocus
                />
              </div>
            </div>

            <button type="submit" className="auth-submit" disabled={loading}>
              {loading ? (
                <div className="loading-spinner"></div>
              ) : (
                <>
                  <LogIn size={18} />
                  <span>Verify & Login</span>
                </>
              )}
            </button>

            <div className="auth-footer" style={{ marginTop: '1rem' }}>
              Didn't get the code? 
              <span className="auth-link" onClick={() => authService.resendOtp(formData.email)}>Resend OTP</span>
            </div>

            <span className="auth-link" onClick={() => setIsOtpStage(false)} style={{ display: 'block', textAlign: 'center', marginTop: '1rem', cursor: 'pointer' }}>
              Go Back
            </span>
          </form>
        )}

        {!isOtpStage && (
          <div className="auth-footer">
            Already have an account? 
            <Link to="/login" className="auth-link">Sign In</Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default Register;


