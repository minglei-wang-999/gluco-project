const env = require('../../env')
const api = require('../../utils/api')

Page({
  data: {
    mealData: null,
    showPoster: false,
    qrCodeUrl: null,
    statusBarHeight: 0,
    navBarHeight: 0,
    displayImage: null,
    isLoading: false
  },

  onLoad(options) {
    // Get system info for navigation bar height
    const systemInfo = wx.getSystemInfoSync();
    const menuButtonInfo = wx.getMenuButtonBoundingClientRect();
    
    // Calculate navigation bar height
    const statusBarHeight = systemInfo.statusBarHeight;
    const navBarHeight = (menuButtonInfo.top - statusBarHeight) * 2 + menuButtonInfo.height;
    
    this.setData({
      statusBarHeight,
      navBarHeight
    });

    console.log('Poster page onLoad - options:', options);
    console.log('mealData parameter length:', options.mealData ? options.mealData.length : 'undefined');

    if (options.mealData) {
      try {
        // Log the raw mealData for debugging
        console.log('Raw mealData:', options.mealData);
        
        // Check if the data is already decoded (some platforms might auto-decode)
        let decodedData = options.mealData;
        try {
          // First try to decode if it's still encoded
          decodedData = decodeURIComponent(options.mealData);
          console.log('Decoded mealData:', decodedData);
        } catch (decodeErr) {
          console.log('Data appears to be already decoded, using as-is');
        }
        
        const mealData = JSON.parse(decodedData);
        console.log('Parsed mealData:', mealData);
        
        // Validate required fields
        if (!mealData.name) {
          throw new Error('Missing required field: name');
        }
        
        const qrCodeUrl = env.qrcodeUrl;
        this.setData({ mealData, qrCodeUrl });
        
        // Get temp URL for display if we have a cloud file ID
        if (mealData.image) {
          this.refreshTempUrl(mealData.image);
        }
      } catch (err) {
        console.error('Error parsing meal data:', err);
        console.error('Error details:', {
          message: err.message,
          stack: err.stack,
          mealDataLength: options.mealData ? options.mealData.length : 'undefined',
          mealDataPreview: options.mealData ? options.mealData.substring(0, 100) + '...' : 'undefined'
        });
        
        // Show more specific error message
        let errorMessage = '参数错误';
        if (err.message.includes('JSON')) {
          errorMessage = '数据格式错误';
        } else if (err.message.includes('Missing required field')) {
          errorMessage = '数据不完整';
        }
        
        wx.showToast({
          title: errorMessage,
          icon: 'error'
        });
        
        // Set a fallback state to prevent the page from being completely broken
        this.setData({
          mealData: {
            name: '餐食分享',
            image: null,
            gl: 0,
            fat: 0,
            protein: 0,
            carbs: 0,
            description: '数据加载失败'
          }
        });
      }
    } else {
      console.log('No mealData provided in options');
      wx.showToast({
        title: '缺少分享数据',
        icon: 'error'
      });
    }
  },

  onShow() {
    // Get temp URL for display if we have a cloud file ID
    if (this.data.mealData && this.data.mealData.image) {
      this.refreshTempUrl(this.data.mealData.image);
    }
  },

  refreshTempUrl(cloudFileId) {
    if (!cloudFileId) {
      console.error('No cloud file ID provided');
      return;
    }

    this.setData({ isLoading: true });
    
    const app = getApp();
    
    // Check if user is logged in, if not, login first
    if (!app.globalData.token) {
      console.log('User not logged in, attempting login before getTempUrl');
      app.login((success) => {
        if (success) {
          console.log('Login successful, now getting temp URL');
          this.doGetTempUrl(cloudFileId);
        } else {
          console.error('Login failed');
          this.setData({ isLoading: false });
          wx.showToast({
            title: '登录失败，请重试',
            icon: 'error'
          });
        }
      });
    } else {
      // User is already logged in, proceed with getTempUrl
      this.doGetTempUrl(cloudFileId);
    }
  },

  doGetTempUrl(cloudFileId) {
    console.log('Converting cloud file ID to temporary URL:', cloudFileId);
    api.getTempUrl(cloudFileId)
      .then(res => {
        if (res && res.temp_url) {
          console.log('Generated temporary URL:', res.temp_url);
          this.setData({
            displayImage: res.temp_url, // Update only displayImage with temp URL
            showPoster: true,
            isLoading: false
          });
        } else {
          throw new Error('Failed to get temporary URL for image');
        }
      })
      .catch(err => {
        console.error('Error getting temporary URL:', err);
        this.setData({ isLoading: false });
        wx.showToast({
          title: '图片加载失败',
          icon: 'error'
        });
      });
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage: function() {
    console.log('onShareAppMessage');
    // Share the original cloud file ID, not the temp URL
    const shareData = {
      ...this.data.mealData,
      image: this.data.mealData.image // Keep original cloud file ID for sharing
    };
    return {
      title: this.data.mealData.name,
      path: '/pages/poster/index?mealData=' + encodeURIComponent(JSON.stringify(shareData))
    }
  },

  onShareTimeline: function() {
    console.log('onShareTimeline');
    // Share the original cloud file ID, not the temp URL
    const shareData = {
      ...this.data.mealData,
      image: this.data.mealData.image // Keep original cloud file ID for sharing
    };
    return {
      title: this.data.mealData.name,
      query: 'mealData=' + encodeURIComponent(JSON.stringify(shareData))
    }
  },

  onBack() {
    wx.navigateBack({
      fail: () => {
        // If navigateBack fails (no pages in stack), navigate to home page
        wx.switchTab({
          url: '/pages/dashboard/index'
        });
      }
    });
  },

  onStartUsing() {
    wx.switchTab({
      url: '/pages/camera/index'
    });
  }
}); 