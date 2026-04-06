import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add JWT token to headers if available
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle common errors (like expired tokens)
client.interceptors.response.use(
  (response) => {
    return response.data; // Return just the data part of the response
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and possibly redirect to login if session expires
      // localStorage.removeItem('access_token');
      // localStorage.removeItem('user');
    }
    return Promise.reject(error);
  }
);

export default client;
