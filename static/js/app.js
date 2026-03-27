/**
 * Entorhino — Frontend JavaScript
 * Token management, API client, dashboard routing, voice recognition.
 */

// ══════════════════════════════════════════════════════════════
// Auth & Token Management
// ══════════════════════════════════════════════════════════════

const API = '/api';

function getTokens() {
  const data = localStorage.getItem('entorhino_auth');
  return data ? JSON.parse(data) : null;
}

function setTokens(data) {
  localStorage.setItem('entorhino_auth', JSON.stringify(data));
}

function getUser() {
  const auth = getTokens();
  return auth ? auth.user : null;
}

function logout() {
  localStorage.removeItem('entorhino_auth');
  window.location.href = '/';
}

function requireAuth() {
  const auth = getTokens();
  if (!auth || !auth.access_token) {
    window.location.href = '/';
    return false;
  }
  return true;
}

// ══════════════════════════════════════════════════════════════
// API Client
// ══════════════════════════════════════════════════════════════

async function apiFetch(path, options = {}) {
  const auth = getTokens();
  const headers = { ...(options.headers || {}) };

  if (auth?.access_token) {
    headers['Authorization'] = `Bearer ${auth.access_token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const res = await fetch(`${API}${path}`, { ...options, headers });

    // Handle token refresh on 401
    if (res.status === 401 && auth?.refresh_token) {
      const refreshRes = await fetch(`${API}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: auth.refresh_token }),
      });
      if (refreshRes.ok) {
        const newAuth = await refreshRes.json();
        setTokens(newAuth);
        headers['Authorization'] = `Bearer ${newAuth.access_token}`;
        const retry = await fetch(`${API}${path}`, { ...options, headers });
        return retry;
      } else {
        logout();
        return res;
      }
    }
    return res;
  } catch (err) {
    showToast('Network error. Please try again.', 'error');
    throw err;
  }
}

async function apiGet(path) {
  const res = await apiFetch(path);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

async function apiPost(path, data) {
  const isFormData = data instanceof FormData;
  const res = await apiFetch(path, {
    method: 'POST',
    body: isFormData ? data : JSON.stringify(data),
  });
  const json = await res.json().catch(() => ({ detail: 'Request failed' }));
  if (!res.ok) throw new Error(json.detail || 'Request failed');
  return json;
}

async function apiPut(path, data) {
  const res = await apiFetch(path, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  const json = await res.json().catch(() => ({ detail: 'Request failed' }));
  if (!res.ok) throw new Error(json.detail || 'Request failed');
  return json;
}

async function apiDelete(path) {
  const res = await apiFetch(path, { method: 'DELETE' });
  const json = await res.json().catch(() => ({ detail: 'Request failed' }));
  if (!res.ok) throw new Error(json.detail || 'Request failed');
  return json;
}

// ══════════════════════════════════════════════════════════════
// Toast Notifications
// ══════════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ══════════════════════════════════════════════════════════════
// Voice Recognition (Web Speech API)
// ══════════════════════════════════════════════════════════════

class VoiceRecognition {
  constructor(options = {}) {
    this.onResult = options.onResult || (() => { });
    this.onStart = options.onStart || (() => { });
    this.onEnd = options.onEnd || (() => { });
    this.recognition = null;
    this.isRecording = false;
    this.mode = 'none'; // 'speech-api' or 'media-recorder'
    this.mediaRecorder = null;
    this.audioChunks = [];

    // Try Web Speech API first (Chrome, Edge, Safari)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.mode = 'speech-api';
      this.recognition = new SpeechRecognition();
      this.recognition.lang = 'en-IN';
      this.recognition.continuous = true;
      this.recognition.interimResults = true;

      this.recognition.onresult = (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        this.onResult(transcript, event.results[event.results.length - 1].isFinal);
      };

      this.recognition.onend = () => {
        this.isRecording = false;
        this.onEnd();
      };

      this.recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        this.isRecording = false;
        this.onEnd();
        if (event.error === 'not-allowed') {
          showToast('Microphone access denied. Please allow microphone access.', 'error');
        }
      };
    } else if (typeof MediaRecorder !== 'undefined') {
      // Fallback: MediaRecorder (works in ALL modern browsers including Firefox)
      this.mode = 'media-recorder';
      this.recognition = true; // Signal that voice is available
    } else {
      console.warn('Neither Speech API nor MediaRecorder supported');
    }
  }

  async start() {
    if (this.mode === 'speech-api') {
      this.recognition.start();
      this.isRecording = true;
      this.onStart();
    } else if (this.mode === 'media-recorder') {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioChunks = [];
        // Use supported MIME type
        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' :
          MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : '';
        this.mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

        this.mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) this.audioChunks.push(e.data);
        };

        this.mediaRecorder.onstop = async () => {
          stream.getTracks().forEach(t => t.stop());
          this.isRecording = false;

          // Send audio to backend for Whisper transcription
          const blob = new Blob(this.audioChunks, { type: mimeType || 'audio/webm' });
          this.onResult('🔄 Transcribing...', false);

          try {
            const formData = new FormData();
            formData.append('audio', blob, `recording.${mimeType === 'audio/mp4' ? 'mp4' : 'webm'}`);
            const token = JSON.parse(localStorage.getItem('entorhino_auth'))?.access_token;
            const resp = await fetch('/api/tests/transcribe', {
              method: 'POST',
              headers: { 'Authorization': `Bearer ${token}` },
              body: formData,
            });
            const data = await resp.json();
            if (data.text) {
              this.onResult(data.text, true);
            } else {
              this.onResult('', true);
              showToast('Could not transcribe audio', 'warning');
            }
          } catch (err) {
            showToast('Transcription failed: ' + err.message, 'error');
            this.onResult('', true);
          }
          this.onEnd();
        };

        this.mediaRecorder.start(1000);
        this.isRecording = true;
        this.onStart();
      } catch (err) {
        showToast('Microphone access denied. Please allow microphone access.', 'error');
        this.onEnd();
      }
    } else {
      showToast('Voice recognition not supported in this browser. Please type your answer.', 'warning');
    }
  }

  stop() {
    if (this.mode === 'speech-api' && this.recognition && this.isRecording) {
      this.recognition.stop();
    } else if (this.mode === 'media-recorder' && this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
    }
  }

  toggle() {
    if (this.isRecording) this.stop();
    else this.start();
  }
}

// ══════════════════════════════════════════════════════════════
// Utility Helpers
// ══════════════════════════════════════════════════════════════

function $(selector) { return document.querySelector(selector); }
function $$(selector) { return document.querySelectorAll(selector); }

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function setLoading(btn, loading) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Loading...';
  } else {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
  }
}

// ══════════════════════════════════════════════════════════════
// Mobile Sidebar Toggle
// ══════════════════════════════════════════════════════════════

function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  if (sidebar) sidebar.classList.toggle('open');
}

// Click outside to close
document.addEventListener('click', (e) => {
  const sidebar = document.querySelector('.sidebar');
  const hamburger = document.querySelector('.hamburger');
  if (sidebar && sidebar.classList.contains('open') &&
    !sidebar.contains(e.target) && !hamburger?.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});
