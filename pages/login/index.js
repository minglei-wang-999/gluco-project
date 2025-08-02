const api = require('../../utils/api')

const app = getApp()

Page({
  data: {
    isLoading: false,
    invite_code: ''
  },

  onLoad() {
    console.log('Login page loaded')
    // Check if already logged in
    if (app.globalData.token) {
      console.log('Token found, redirecting to home')
      // Add a small delay to ensure app is initialized
      setTimeout(() => {
        this.redirectToHome()
      }, 100)
    }
  },

  onInviteCodeInput(e) {
    this.setData({ invite_code: e.detail.value });
  },

  handleLogin: function() {
    this.setData({ isLoading: true });
    console.log('login start')
    const invite_code = this.data.invite_code;
    app.login((success) => {
      console.log('login success', success)
      this.setData({ isLoading: false });
      
      if (success) {
        // Redirect to appropriate page after login
        wx.switchTab({
          url: '/pages/dashboard/index'
        });
      } else {
        wx.showToast({
          title: '登录失败，请重试',
          icon: 'none'
        });
      }
    }, invite_code);
  },

  redirectToHome() {
    console.log('Redirecting to home page')
    wx.switchTab({
      url: '/pages/dashboard/index',
      success: () => console.log('Navigation to home successful'),
      fail: (error) => {
        console.error('Navigation failed:', error)
        this.setData({
          error: '页面跳转失败，请重试'
        })
      }
    })
  }
}) 