const DEFAULT_SUBSCRIPTION_PLANS = {
  monthly: {
    id: 'monthly',
    name: '月度会员',
    duration: 30,
    price: 9.9,
    description: '可使用30天，支持随时升级',
    features: [
      '每日上传5张图片',
      '所有系统功能',
      '客服支持',
      '可升级年付',
      '可升级终身会员'
    ]
  },
  yearly: {
    id: 'yearly',
    name: '年付会员',
    duration: 365,
    price: 99,
    description: '年付更优惠，支持随时升级',
    features: [
      '每日上传5张图片',
      '所有系统功能',
      '客服支持',
      '节省17%',
      '可升级终身会员'
    ]
  },
  lifetime: {
    id: 'lifetime',
    name: '终身会员',
    duration: 'lifetime',
    price: 199,
    description: '一次付费，终身使用',
    features: [
      '每日上传5张图片',
      '所有系统功能',
      '客服支持',
      '最佳性价比',
      '永久免费更新'
    ]
  }
};

const MOCK_USER_SUBSCRIPTION = {
  status: 'none', // 'active', 'expired', 'none'
  planId: '', // 'monthly', 'yearly', 'lifetime'
  expiresAt: null,
  nextExpiresAt: null
};

module.exports = {
  DEFAULT_SUBSCRIPTION_PLANS,
  MOCK_USER_SUBSCRIPTION
}; 