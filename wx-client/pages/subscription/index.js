const app = getApp();
const api = require('../../utils/api');

Page({
  data: {
    isLoading: true,
    plans: [],
    plansError: null
  },

  onLoad: function(options) {
    this.loadSubscriptionData();
  },

  loadSubscriptionData: function() {
    this.setData({ isLoading: true });
    
    // Load subscription status which now includes available plans
    if (app.globalData.isLogin) {
      app.fetchSubscriptionInfo()
        .then((result) => {
          console.log('Fetched subscription data:', result);
          if (!result.availableActions) {
            throw new Error('Invalid subscription data received');
          }

          this.setData({ 
            plans: result.availableActions,
            isLoading: false 
          });
        })
        .catch(error => {
          console.error('Failed to load subscription:', error);
          this.setData({ 
            isLoading: false,
            plans: [],
            plansError: '获取订阅方案失败，请稍后再试'
          });
        });
    } else {
      // If not logged in, fetch plans directly
      api.getUserSubscription()
        .then(result => {
          console.log('Fetched subscription plans:', result);
          if (!result.available_actions) {
            throw new Error('Invalid subscription data received');
          }

          this.setData({ 
            plans: result.available_actions,
            isLoading: false 
          });
        })
        .catch(error => {
          console.error('Failed to fetch subscription plans:', error);
          this.setData({ 
            plans: [],
            isLoading: false,
            plansError: '获取订阅方案失败，请稍后再试'
          });
        });
    }
  },

  onPlanSelected: function(e) {
    const plan = e.currentTarget.dataset.plan;
    const isUpgrade = plan.action === 'upgrade';

    wx.showModal({
      title: isUpgrade ? '确认升级' : '确认订阅',
      content: `您选择了${plan.name}，费用 ¥${plan.payment}`,
      confirmText: '确认支付',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '准备支付...' });
          
          // Get payment info using new endpoint
          api.getSubscriptionPayment({
            action: plan.action,
            plan_id: plan.planId,
            name: plan.name,
            price: plan.price,
            duration: plan.duration,
            description: plan.description,
            credit: plan.credit || 0,
            payment: plan.payment
          })
          .then(result => {
            // Start payment with returned parameters
            console.log('Payment params:', result);
            const paymentParams = {
              appId: result.appId,
              timeStamp: result.timeStamp,
              nonceStr: result.nonceStr,
              package: result.package,
              signType: result.signType,
              paySign: result.paySign
            };

            wx.requestPayment({
              ...paymentParams,
              success: (payRes) => {
                wx.showLoading({ title: '确认支付结果...' });
                
                // Store subscription ID for status polling
                this._pendingSubscriptionId = result.subscription_id;
                
                // Poll subscription status to confirm payment
                this.pollSubscriptionStatus(10, () => {
                  wx.hideLoading();
                  wx.showToast({
                    title: isUpgrade ? '升级成功' : '订阅成功',
                    icon: 'success',
                    duration: 1500,
                    complete: () => {
                      // Just navigate back, let settings page refresh in onShow
                      setTimeout(() => {
                        wx.navigateBack({
                          delta: 1
                        });
                      }, 500); // Small delay to ensure toast is visible
                    }
                  });
                });
              },
              fail: (payError) => {
                console.error('Payment failed:', payError);
                wx.hideLoading();
                if (payError.errMsg.indexOf('cancel') > -1) {
                  wx.showToast({
                    title: '支付已取消',
                    icon: 'none'
                  });
                } else {
                  wx.showModal({
                    title: '支付失败',
                    content: '支付遇到问题，请稍后重试或联系客服',
                    showCancel: false,
                    confirmText: '我知道了'
                  });
                }
              }
            });
          })
          .catch(error => {
            console.error('Failed to get payment info:', error);
            wx.hideLoading();
            wx.showModal({
              title: '订阅失败',
              content: '获取支付信息时遇到问题，请稍后重试或联系客服',
              showCancel: false,
              confirmText: '我知道了'
            });
          });
        }
      }
    });
  },

  // Poll subscription status to confirm payment
  pollSubscriptionStatus: function(maxAttempts, onSuccess) {
    let attempts = 0;
    
    const checkStatus = () => {
      attempts++;
      
      const currentPlan = app.globalData.subscription;
      console.log('currentPlan', currentPlan);
      
      app.fetchSubscriptionInfo()
        .then(subscription => {
          console.log('subscription', subscription);
          // Check if subscription is active and plan has changed
          if (subscription.status === 'active' && 
              (subscription.planId !== currentPlan.planId || subscription.nextExpiresAt )) {
            onSuccess();
          } else if (attempts < maxAttempts) {
            // Try again in 1 second
            setTimeout(checkStatus, 1000);
          } else {
            wx.hideLoading();
            wx.showModal({
              title: '确认支付状态',
              content: '支付可能已成功，但状态更新较慢。请稍后在"我的订阅"中查看，如有问题请联系客服',
              showCancel: false,
              confirmText: '我知道了'
            });
          }
        })
        .catch(error => {
          console.error('Failed to check subscription status:', error);
          if (attempts < maxAttempts) {
            setTimeout(checkStatus, 1000);
          } else {
            wx.hideLoading();
            wx.showModal({
              title: '确认支付状态',
              content: '无法确认支付状态，请稍后在"我的订阅"中查看，如有问题请联系客服',
              showCancel: false,
              confirmText: '我知道了'
            });
          }
        });
    };
    
    checkStatus();
  },

  onContactSupport: function() {
    wx.showModal({
      title: '联系客服',
      content: '如需帮助，请添加客服微信：@rossywang',
      showCancel: false
    });
  },

  onRetry: function() {
    this.loadSubscriptionData();
  }
}); 