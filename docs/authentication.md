# Authentication Implementation

This document outlines the authentication architecture used in the GL Tracker WeChat Mini Program.

## Overview

The authentication system follows a clean separation of concerns pattern:

1. **API Module (`utils/api.js`)**: Handles raw HTTP requests to the backend
2. **App Instance (`app.js`)**: Manages the full login flow and application state
3. **Pages**: Use `app.login()` for a consistent authentication experience

## Authentication Flow

## Token Management

1. **Storage**: Tokens are stored in both the app's global state and in WeChat's storage system:
   ```javascript
   // Store token
   wx.setStorageSync('token', token);
   this.globalData.token = token;
   ```

2. **Retrieval**: On app launch, we check for existing tokens:
   ```javascript
   onLaunch: function () {
     // Check if user has a valid token in storage
     const token = wx.getStorageSync('token');
     if (token) {
       this.globalData.token = token;
       this.globalData.isLogin = true;
     }
   }
   ```

3. **Usage**: The request function automatically adds the token to authenticated requests:
   ```javascript
   if (needToken) {
     const token = app.globalData.token;
     if (!token) {
       reject(new Error('No token available'));
       return;
     }
     header.Authorization = `Bearer ${token}`;
   }
   ```

4. **Expiration**: Token expiration is handled in the request function:
   ```javascript
   if (res.statusCode === 401) {
     // Token expired or invalid
     app.globalData.token = null;
     app.globalData.isLogin = false;
     wx.removeStorageSync('token');
     
     // Redirect to login page
     wx.showToast({
       title: '登录已过期，请重新登录',
       icon: 'none',
       duration: 2000
     });
     
     reject(new Error('Unauthorized'));
   }
   ```

## Best Practices

1. **Separation of Concerns**: API calls are separated from application logic
2. **Consistent Interface**: All pages use `app.login()` for authentication
3. **Error Handling**: Login failures are properly reported back to the UI
4. **Token Management**: Tokens are securely stored and automatically refreshed when expired

## Future Improvements

Potential enhancements to the authentication system:

1. **Refresh Tokens**: Implement token refresh to extend sessions without requiring re-login
2. **Session Timeout**: Implement automatic logout after a period of inactivity