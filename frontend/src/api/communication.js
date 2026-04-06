import client from './client';

const communicationService = {
  // Feedback Methods
  getMyTeachers: async () => {
    const response = await client.get('/feedback/my-teachers');
    return response;
  },

  submitFeedback: async (feedbackData) => {
    const response = await client.post('/feedback/', feedbackData);
    return response;
  },

  getTeacherFeedback: async (teacherId) => {
    const response = await client.get(`/feedback/teacher/${teacherId}`);
    return response;
  },

  // Alert Methods (System Alerts)
  getAlerts: async () => {
    const response = await client.get('/alerts/');
    return response;
  },

  getUnreadAlertCount: async () => {
    const response = await client.get('/alerts/unread-count');
    return response;
  },

  markAlertRead: async (alertId) => {
    const response = await client.put(`/alerts/${alertId}/read`);
    return response;
  },

  // Announcement Methods (School News)
  getAnnouncements: async () => {
    const response = await client.get('/announcements/');
    return response;
  },

  getUnreadAnnounceCount: async () => {
    const response = await client.get('/announcements/unread-count');
    return response;
  },

  markAnnouncementsRead: async () => {
    const response = await client.put('/announcements/mark-all-read');
    return response;
  },

  markAllRead: async () => {
    // Convenience to mark both as read
    await client.put('/alerts/mark-all-read');
    await client.put('/announcements/mark-all-read');
  }
};

export default communicationService;
