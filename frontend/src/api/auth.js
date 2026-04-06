import client from './client';

const authService = {
  login: async (email, password) => {
    return client.post('/auth/login', { email, password });
  },

  register: async (userData) => {
    return client.post('/auth/register', userData);
  },

  verifyOtp: async (email, code) => {
    return client.post('/auth/verify-otp', { email, code });
  },

  resendOtp: async (email) => {
    return client.post('/auth/resend-otp', { email });
  },

  refreshToken: async (refreshToken) => {
    return client.post('/auth/refresh', { refresh_token: refreshToken });
  }
};

export default authService;
