// API utility functions
let apiConfig = {
  baseUrl: '', // Default value
  envId: '' // Cloud environment ID
};

// Initialize API configuration
const initApi = (config) => {
  apiConfig = { ...apiConfig, ...config };
  console.log('API initialized with config:', apiConfig);
};

// Get app instance only when needed
const getAppData = () => {
  const app = getApp();
  return app ? app.globalData : null;
};

// Cloud container request implementation
const cloudRequest = (url, method, data, header) => {
  return new Promise((resolve, reject) => {
    // Call cloud container
    wx.cloud.callContainer({
      config: {
        env: apiConfig.envId,
      },
      path: `${url}`,
      header: header,
      method: method,
      data: data,
      success: res => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else if (res.statusCode === 401) {
          // Token expired or invalid
          handleUnauthorized(reject);
        } else {
          reject(new Error(`Request failed with status ${res.statusCode}`));
        }
      },
      fail: err => {
        reject(err);
      }
    });
  });
};

// Standard request implementation (existing code)
const standardRequest = (url, method, data, header) => {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${url}`,
      method: method,
      data: data,
      header: header,
      success: res => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else if (res.statusCode === 401) {
          // Token expired or invalid
          handleUnauthorized(reject);
        } else {
          reject(new Error(`Request failed with status ${res.statusCode}`));
        }
      },
      fail: err => {
        reject(err);
      }
    });
  });
};

// Common unauthorized handler to avoid code duplication
const handleUnauthorized = (reject) => {
  apiConfig.token = null;
  
  // Update app global data if available
  const appData = getAppData();
  if (appData) {
    appData.token = null;
    appData.isLogin = false;
  }
  
  wx.removeStorageSync('token');
  
  // Redirect to login page
  wx.showToast({
    title: '登录已过期，请重新登录',
    icon: 'none',
    duration: 2000
  });
  
  reject(new Error('Unauthorized'));
};

// Unified request function that chooses the appropriate implementation
const request = (url, method, data, needToken = true) => {
  const header = {};

  // Add authorization header if token is available and needed
  if (needToken) {
    // Try to get token from config first, then from app if available
    const token = apiConfig.token || (getAppData() && getAppData().token);
    if (!token) {
      reject(new Error('No token available'));
      return;
    }
    header.Authorization = `Bearer ${token}`;
  }

  // Use cloud container in production, standard request in development
  if (apiConfig.baseUrl.startsWith('https://') || apiConfig.baseUrl.startsWith('http://')) {
    console.log('standardRequest');
    header['ngrok-skip-browser-warning'] = true;
    return standardRequest(apiConfig.baseUrl + url, method, data, header);
  } else {
    console.log('cloudRequest');
    header['X-WX-SERVICE'] = getAppData().serviceName;
    return cloudRequest(url, method, data, header);
  }
};

// API methods
const api = {
  // Configuration
  init: initApi,
  
  setToken: (token) => {
    apiConfig.token = token;
  },
  
  // Auth
  weixinLogin: (code, invite_code = null) => {
    // This function only handles the API call to your backend
    const data = { code };
    if (invite_code) data.invite_code = invite_code;
    return request('/weixin/auth/login', 'POST', data, false);
  },
  
  updateProfile: (profileData) => {
    return request('/weixin/auth/profile', 'PUT', profileData);
  },
  
  // Subscription
  getUserSubscription: () => {
    return request('/subscriptions/status', 'GET');
  },

  updateSubscription: (data) => {
    return request('/subscriptions/update', 'POST', data);
  },
  
  getSubscriptionPayment: (data) => {
    return request('/subscriptions/payment', 'POST', data);
  },
  
  // Meals
  getMealHistory: (startTime=null, endTime=null) => {
    let url = '/meals/history';
    if (startTime && endTime) {
      url += `?start_time=${startTime}&end_time=${endTime}`;
    }
    return request(url, 'GET');
  },
  
  getUserMetrics: (startTime, endTime) => {
    return request(`/meals/metrics?start_time=${startTime}&end_time=${endTime}`, 'GET');
  },
  
  saveMeal: (mealData) => {
    return request('/meals', 'POST', mealData);
  },
  
  // Image Processing
  processImage: (fileId, analysis = null, userComment = null) => {
    const data = {
      file_id: fileId
    };
    
    if (analysis) {
      data.analysis = analysis;
    }
    
    if (userComment) {
      data.user_comment = userComment;
    }
    
    return request('/jobs/process-image', 'POST', data);
  },
  
  // Async Image Processing
  processImageAsync: (fileId, analysis = null, userComment = null) => {
    const data = {
      file_id: fileId
    };
    
    if (analysis) {
      data.analysis = analysis;
    }
    
    if (userComment) {
      data.user_comment = userComment;
    }
    
    return request('/jobs/process-image-async', 'POST', data);
  },
  
  // Task Status
  getTaskStatus: (taskId) => {
    return request(`/jobs/tasks/${taskId}`, 'GET');
  },
  
  // Nutrition Query
  queryNutrition: (ingredient) => {
    return request('/jobs/query-nutritions', 'POST', { ingredient });
  },
  
  // Health check
  healthCheck: () => {
    return request('/health', 'GET', null, false);
  },

  // Cloud Storage
  getTempUrl: (cloudId) => {
    return request('/jobs/temp-url', 'POST', { cloud_id: cloudId });
  }
};

module.exports = api; 