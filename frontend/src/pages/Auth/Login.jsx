import React, { useState } from 'react';
import { Mail, Lock, LogIn, AlertCircle } from 'lucide-react';
import logo from '../../assets/logo.png';
import authService from '../../api/auth';
import './Auth.css';

const Login = ({ onSwitch, onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const data = await authService.login(email, password);
      console.log('Login successful:', data);
      
      // Axios client returns response.data directly due to interceptor
      const { access_token, refresh_token, user } = data;
      
      // Store in session
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      onLoginSuccess(user);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password. Please try again.');
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
          <h2>Welcome Back</h2>
          <p>Login to your adaptive learning portal</p>
        </div>

        {error && (
          <div className="error-message">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <div className="input-container">
              <Mail className="input-icon" size={18} />
              <input 
                type="email" 
                className="auth-input" 
                placeholder="name@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <div className="input-container">
              <Lock className="input-icon" size={18} />
              <input 
                type="password" 
                className="auth-input" 
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? (
              <div className="loading-spinner"></div>
            ) : (
              <>
                <LogIn size={18} />
                <span>Sign In</span>
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          Don't have an account? 
          <span className="auth-link" onClick={onSwitch}>Create New ID</span>
        </div>
      </div>
    </div>
  );
};

export default Login;
