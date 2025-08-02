// app.js
// Import the API module
const api = require('./utils/api');
const env = require('./env')

App({
  globalData: {
    envId: env.envId,
    serviceName: 'gluco',
    userInfo: null,
    token: null,
    isLogin: false,
    needRefresh: false,
    subscription: {
      status: 'inactive',
      planId: null,
      expiresAt: null,
      nextExpiresAt: null,
      tier: 'free'
    }
  },

  onLaunch: function () {
    // Get debug status
    const appBaseInfo = wx.getAppBaseInfo ? wx.getAppBaseInfo() : null;
    const isDebug = appBaseInfo ? appBaseInfo.enableDebug : false;
    
    // Initialize cloud environment
    wx.cloud.init({
      env: this.globalData.envId,
      traceUser: true
    });
    
    // Initialize API with configuration
    api.init({
      // For debug mode, set a development baseUrl
      // baseUrl: isDebug ? 'https://gluco-136891-10-1338488478.sh.run.tcloudbase.com' : '',
      baseUrl: '',
      // Configure cloud container settings for production
      envId: this.globalData.envId
    });
    console.log('api.init', api.apiConfig);

    // If you have a token in storage, set it immediately
    const token = wx.getStorageSync('token');
    if (token) {
      api.setToken(token);
      this.globalData.token = token;
      this.globalData.userInfo = wx.getStorageSync('userInfo');
      this.globalData.isLogin = true;
      
      // Load saved subscription or generate mock data
      const savedSubscription = wx.getStorageSync('subscription');
      if (savedSubscription) {
        this.globalData.subscription = savedSubscription;
      } else {
        // Generate mock subscription data on first launch
        this.fetchSubscriptionInfo();
      }
    } else {
      // For testing: Generate mock subscription data even if not logged in
      this.globalData.token = 'mock_token_for_testing';
      this.fetchSubscriptionInfo();
      this.globalData.token = null;
    }
  },

  login: function(callback, invite_code = null) {
    // 1. Get code from WeChat
    wx.login({
      success: (res) => {
        console.log('wx.login success', res)
        if (res.code) {
          // 2. Send code to your backend via API
          api.weixinLogin(res.code, invite_code)
            .then(result => {
              console.log('api.weixinLogin success', result)
              // 3. Store token
              const token = result.access_token;
              wx.setStorageSync('token', token);
              this.globalData.token = token;
              this.globalData.isLogin = true;
              
              // 4. Get user info if needed
              const userInfo = result.user
              // 5. Store user info
              this.globalData.userInfo = userInfo;
              console.log('app.js userInfo', this.globalData.userInfo)
              wx.setStorageSync('userInfo', userInfo)
              
              // 6. Get subscription info
              return this.fetchSubscriptionInfo();
            })
            .then(subscription => {
              console.log('Subscription fetched after login:', subscription);
              if (callback && typeof callback === 'function') {
                callback(true);
              }
            })
            .catch(error => {
              console.error('Login or subscription check failed:', error);
              // If it's a subscription error, we still want to proceed with login
              if (this.globalData.token) {
                console.warn('Login succeeded but subscription check failed');
                if (callback && typeof callback === 'function') {
                  callback(true);
                }
              } else {
                if (callback && typeof callback === 'function') {
                  callback(false);
                }
              }
            });
        } else {
          console.error('wx.login failed:', res.errMsg);
          if (callback && typeof callback === 'function') {
            callback(false);
          }
        }
      },
      fail: (error) => {
        console.error('wx.login failed:', error);
        if (callback && typeof callback === 'function') {
          callback(false);
        }
      }
    });
  },

  logout: function() {
    // Clear token and user data
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    wx.removeStorageSync('subscription');
    this.globalData.needRefresh = true;
    this.globalData.token = null;
    this.globalData.userInfo = null;
    this.globalData.isLogin = false;
    this.globalData.subscription = {
      status: 'inactive',
      planId: null,
      expiresAt: null,
      nextExpiresAt: null,
      tier: 'free'
    };
  },
  
  fetchSubscriptionInfo: function() {
    // Only fetch if user is logged in
    if (!this.globalData.token) return;
    
    const util = require('./utils/util');
    
    // Use the real API to fetch subscription info
    return api.getUserSubscription()
      .then(result => {
        console.log('Raw API subscription info:', result);
        
        // Convert snake_case to camelCase
        const transformedResult = util.snakeToCamel(result);
        console.log('Transformed subscription:', transformedResult);
        
        // Store subscription info
        this.globalData.subscription = transformedResult;
        wx.setStorageSync('subscription', transformedResult);
        return transformedResult;
      })
      .catch(error => {
        console.error('Failed to fetch subscription info:', error);
        // Set default values on error
        const defaultSubscription = {
          status: 'inactive',
          planId: null,
          expiresAt: null,
          nextExpiresAt: null,
          tier: 'free'
        };
        this.globalData.subscription = defaultSubscription;
        wx.setStorageSync('subscription', defaultSubscription);
        return defaultSubscription;
      });
  }
}) 