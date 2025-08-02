// Mock utilities for testing
const mockPaymentSuccess = () => {
  return {
    timeStamp: String(Date.now()),
    nonceStr: 'mock_nonce',
    package: 'mock_package',
    signType: 'MD5',
    paySign: 'mock_sign',
  };
};

const mockPaymentParams = {
  success: mockPaymentSuccess(),
  fail: {
    errMsg: 'requestPayment:fail cancel',
  },
};

// Mock the wx.requestPayment API
const mockRequestPayment = (options) => {
  console.log('Mock payment called with options:', options);
  
  // Simulate network delay
  setTimeout(() => {
    if (wx.mockPaymentShouldSucceed !== false) {
      options.success(mockPaymentParams.success);
    } else {
      options.fail(mockPaymentParams.fail);
    }
  }, 1000);
};

module.exports = {
  mockPaymentParams,
  mockRequestPayment,
  // Helper to control payment behavior
  setMockPaymentSuccess: (shouldSucceed) => {
    wx.mockPaymentShouldSucceed = shouldSucceed;
  }
}; 