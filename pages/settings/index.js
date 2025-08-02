// pages/settings/index.js
const env = require('../../env')
const app = getApp();

Page({

  /**
   * 页面的初始数据
   */
  data: {
    isLoading: true,
    userInfo: null,
    isLogin: false,
    isIOS: false,
    settings: {
      darkMode: false,
      notificationsEnabled: true,
      dailyGLGoal: 100,
      language: 'zh-CN',
      units: 'metric'
    },
    appInfo: {
      version: '1.0.0',
      buildNumber: '101',
      isDev: env.envId.startsWith('dev-')
    },
    subscription: null,
    showPlanSelector: false,
    availableActions: []
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function(options) {
    const globalData = app.globalData;
    console.log(globalData);
    
    // Detect iOS platform
    const systemInfo = wx.getSystemInfoSync();
    const isIOS = systemInfo.platform === 'ios';
    
    this.setData({
      isLogin: globalData.isLogin,
      userInfo: {...globalData.userInfo},
      isLoading: false,
      isIOS: isIOS
    });
    console.log(this.data.userInfo);
    console.log('Platform detected:', systemInfo.platform, 'isIOS:', isIOS);
    this.loadUserData();
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady: function() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow: function() {
    const globalData = app.globalData;
    // Refresh login status and user info
    this.setData({
      isLogin: globalData.isLogin,
      userInfo: {...globalData.userInfo}
    });
    
    // Get the latest subscription data from API
    if (globalData.isLogin) {
      app.fetchSubscriptionInfo().then(subscription => {
        console.log('Received subscription data:', subscription);
        // Format the expiry date before setting the data
        const formattedSubscription = {
          ...subscription,
          formattedExpiryDate: this.formatExpiryDate(subscription.expiresAt),
          formattedNextExpiryDate: this.formatExpiryDate(subscription.nextExpiresAt)
        };
        this.setData({ 
          subscription: formattedSubscription,
          availableActions: subscription.availableActions
        });
      });
    }
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide: function() {

  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload: function() {

  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh: function() {

  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom: function() {

  },

  onTapLogin: function() {
    wx.showToast({ title: '登录功能开发中', icon: 'none' });
  },
  
  onTapLogout: function() {
    app.logout();
    setTimeout(() => {
      wx.redirectTo({
        url: '/pages/login/index',
        success: () => console.log('Navigation to login successful'),
        fail: (error) => {
          console.error('Navigation failed:', error)
          this.setData({
            error: '页面跳转失败，请重试'
          })
        }
      }, 500)});
  },
  
  onToggleNotifications: function(e) {
    const newValue = e.detail.value;
    this.setData({
      'settings.notificationsEnabled': newValue
    });
    
    // In real app, would save this to server/local storage
    wx.showToast({
      title: newValue ? '通知已开启' : '通知已关闭',
      icon: 'success'
    });
  },
  
  onToggleDarkMode: function(e) {
    const newValue = e.detail.value;
    this.setData({
      'settings.darkMode': newValue
    });
    
    // In real app, would apply theme change
    wx.showToast({
      title: newValue ? '深色模式已开启' : '浅色模式已开启',
      icon: 'success'
    });
  },
  
  onTapGLGoal: function() {
    wx.showActionSheet({
      itemList: ['80', '100', '120', '140', '自定义'],
      success: (res) => {
        if (res.tapIndex === 4) {
          // Custom value
          wx.showModal({
            title: '设置每日GL目标',
            placeholderText: '请输入目标值',
            editable: true,
            success: (res) => {
              if (res.confirm && res.content) {
                const goal = parseInt(res.content);
                if (!isNaN(goal) && goal > 0) {
                  this.setData({
                    'settings.dailyGLGoal': goal
                  });
                }
              }
            }
          });
        } else {
          // Preset value
          const goals = [80, 100, 120, 140];
          this.setData({
            'settings.dailyGLGoal': goals[res.tapIndex]
          });
        }
      }
    });
  },
  
  onTapLanguage: function() {
    wx.showActionSheet({
      itemList: ['简体中文', 'English'],
      success: (res) => {
        const languages = ['zh-CN', 'en-US'];
        this.setData({
          'settings.language': languages[res.tapIndex]
        });
        
        wx.showToast({
          title: '语言已更改',
          icon: 'success'
        });
      }
    });
  },
  
  onTapUnits: function() {
    wx.showActionSheet({
      itemList: ['公制', '英制'],
      success: (res) => {
        const units = ['metric', 'imperial'];
        this.setData({
          'settings.units': units[res.tapIndex]
        });
        
        wx.showToast({
          title: '单位已更改',
          icon: 'success'
        });
      }
    });
  },
  
  onTapFeedback: function() {
    wx.showToast({
      title: '反馈功能将在实际开发中实现',
      icon: 'none'
    });
  },
  
  onTapHelp: function() {
    wx.showToast({
      title: '帮助功能将在实际开发中实现',
      icon: 'none'
    });
  },
  
  onTapAbout: function() {
    wx.showModal({
      title: '关于糖分吃饭助手',
      content: `版本: ${this.data.appInfo.version}\n构建号: ${this.data.appInfo.buildNumber}\n`,
      showCancel: false
    });
  },
  
  // Format expiry date for display
  formatExpiryDate: function(dateString) {
    console.log('Formatting expiry date:', dateString);
    console.log('Subscription data at format time:', this.data.subscription);
    
    if (!dateString) {
      console.log('No date string provided');
      return '';
    }
    
    try {
      console.log('Attempting to parse date:', dateString);
      const date = new Date(dateString);
      console.log('Parsed date object:', date);
      console.log('Date is valid:', !isNaN(date.getTime()));
      
      const year = date.getFullYear();
      const month = date.getMonth() + 1;
      const day = date.getDate();
      console.log('Extracted date parts:', { year, month, day });
      
      // Calculate days remaining
      const today = new Date();
      const daysRemaining = Math.ceil((date - today) / (1000 * 60 * 60 * 24));
      console.log('Days remaining calculation:', {
        date: date.toISOString(),
        today: today.toISOString(),
        daysRemaining
      });
      
      let result;
      if (daysRemaining > 365) {
        result = `永久使用`;
      } else if (daysRemaining > 0) {
        result = `${year}年${month}月${day}日 (还剩${daysRemaining}天)`;
      } else if (daysRemaining === 0) {
        result = `${year}年${month}月${day}日 (今天到期)`;
      } else {
        result = `${year}年${month}月${day}日 (已过期)`;
      }
      console.log('Formatted result:', result);
      return result;
    } catch (e) {
      console.error('Error formatting date:', e);
      console.error('Error details:', e.message);
      console.error('Error stack:', e.stack);
      return '无效日期';
    }
  },
  
  // Debug function to show subscription details
  onTapSubscriptionDetails: function() {
    const subscription = app.globalData.subscription;
    
    // Show detailed subscription info for debugging
    wx.showModal({
      title: '订阅详情（调试信息）',
      content: `会员等级: ${subscription.tier}\n到期日期: ${subscription.expiryDate || '无限期'}\n\n原始数据: ${JSON.stringify(subscription)}`,
      showCancel: false
    });
  },
  
  // Handle subscription upgrade
  onTapUpgradeSubscription: function() {
    // For testing purposes, cycle through subscription tiers
    const currentTier = this.data.subscription.tier;
    let newTier, newExpiryDate;
    
    // Cycle through tiers: free -> basic -> premium -> free
    if (currentTier === 'free') {
      newTier = 'basic';
      // Set expiry date to 3 months from now
      const expiryDate = new Date();
      expiryDate.setMonth(expiryDate.getMonth() + 3);
      newExpiryDate = expiryDate.toISOString();
    } else if (currentTier === 'basic') {
      newTier = 'premium';
      // Set expiry date to 1 year from now
      const expiryDate = new Date();
      expiryDate.setFullYear(expiryDate.getFullYear() + 1);
      newExpiryDate = expiryDate.toISOString();
    } else {
      newTier = 'free';
      newExpiryDate = null;
    }
    
    // Update subscription in global data and local state
    app.globalData.subscription = {
      tier: newTier,
      expiryDate: newExpiryDate
    };
    
    // Update local state
    this.setData({
      subscription: {
        tier: newTier,
        expiryDate: newExpiryDate
      }
    });
    
    // Save to storage
    wx.setStorageSync('subscription', app.globalData.subscription);
    
    // Show toast message
    wx.showToast({
      title: `已升级至${newTier === 'free' ? '免费版' : newTier === 'basic' ? '基础版' : '高级版'}`,
      icon: 'success'
    });
    
    // Original implementation (commented out for testing)
    // wx.showModal({
    //   title: '升级会员',
    //   content: '会员升级功能将在实际开发中实现。',
    //   showCancel: false
    // });
  },
  
  // Manually refresh subscription data (for testing)
  refreshSubscription: function() {
    if (!this.data.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }
    
    wx.showLoading({
      title: '刷新中...',
    });
    
    // Call the mock data function
    app.fetchSubscriptionInfo();
    
    // Update after a short delay
    setTimeout(() => {
      this.setData({
        subscription: {...app.globalData.subscription}
      });
      
      wx.hideLoading();
      wx.showToast({
        title: '刷新成功',
        icon: 'success'
      });
    }, 1000);
  },

  loadUserData: function() {
    if (app.globalData.isLogin) {
      app.fetchSubscriptionInfo().then(subscription => {
        console.log('Loaded subscription data:', subscription);
        // Format the expiry date before setting the data
        const formattedSubscription = {
          ...subscription,
          formattedExpiryDate: this.formatExpiryDate(subscription.expiresAt)
        };
        this.setData({
          isLoading: false,
          subscription: formattedSubscription
        });
      });
    } else {
      const defaultSubscription = {
        status: 'inactive',
        planId: null,
        expiresAt: null,
        nextExpiresAt: null,
        tier: 'free',
        formattedExpiryDate: ''
      };
      this.setData({
        isLoading: false,
        subscription: defaultSubscription
      });
    }
  },

  onSubscribe: function() {
    this.setData({ showPlanSelector: true });
  },

  onRenewal: function() {
    this.setData({ showPlanSelector: true });
  },

  onUpgrade: function() {
    this.setData({ showPlanSelector: true });
  },

  onPlanSelected: function(e) {
    const { plan, isUpgrade } = e.detail;

    wx.showModal({
      title: isUpgrade ? '确认升级' : '确认订阅',
      content: `您选择了${plan.name}，费用 ¥${plan.price}`,
      confirmText: '确认支付',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...' });
          
          // Simulate payment process
          setTimeout(() => {
            const expiryDate = new Date();
            expiryDate.setDate(expiryDate.getDate() + parseInt(plan.duration));
            
            const newSubscription = {
              status: 'active',
              planId: plan.id,
              planName: plan.name,
              expiresAt: expiryDate.toISOString(),
              nextExpiresAt: null,
              tier: plan.id === 'lifetime' ? 'premium' : 'basic'
            };
            
            this.setData({
              subscription: newSubscription,
              showPlanSelector: false
            });

            // Update global data
            app.globalData.subscription = newSubscription;
            
            // Save to storage
            wx.setStorageSync('subscription', newSubscription);

            wx.hideLoading();
            wx.showToast({
              title: '订阅成功',
              icon: 'success'
            });
          }, 1500);
        }
      }
    });
  },


  onTapSubscribe: function() {
    wx.navigateTo({
      url: '/pages/subscription/index'
    });
  }
})