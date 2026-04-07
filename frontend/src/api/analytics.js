import client from './client';

const analyticsService = {
  getStudentDashboard: async (studentId) => {
    const response = await client.get(`/analytics/student/${studentId}`);
    return response;
  },
  
  getClassInsights: async (sectionId) => {
    const response = await client.get(`/analytics/class/${sectionId}`);
    return response;
  },

  getLeaderboard: async () => {
    const response = await client.get('/analytics/leaderboard');
    return response;
  }
};

export default analyticsService;
