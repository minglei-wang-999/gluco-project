# Request Methods: Standard vs. Cloud Container

This document explains the two request methods implemented in GL Tracker WeChat Mini Program and how they integrate with our authentication system.

## Overview

GL Tracker supports two different request methods to accommodate both local development and production environments:

1. **Standard Request (`wx.request`)**: The general HTTP request API used primarily during local development
2. **Cloud Container Request (`wx.cloud.callContainer`)**: Optimized for WeChat Cloud container services, used in production

## Comparison of Request Methods

| Feature | wx.request | wx.cloud.callContainer |
|---------|-----------|------------------------|
| Purpose | General HTTP requests to any server | Specifically for WeChat Cloud container services |
| Authentication | Requires manual header configuration | Simplified for cloud services |
| URL Format | Full URL with base URL + endpoint | Path-based with environment configuration |
| Local Development | ✅ Works without cloud setup | ❌ Requires cloud environment |
| Production Use | ✅ Possible but not optimized | ✅ Recommended for cloud deployment |
| Headers | Fully customizable | Simplified with cloud-specific headers |

## Implementation Architecture

Our implementation in `utils/api.js` provides a unified interface that can switch between the two request methods:

```javascript
// Unified request function that chooses the appropriate implementation
const request = (url, method, data, needToken = true) => {
  // Use cloud container in production, standard request in development
  if (apiConfig.useCloudContainer) {
    return cloudRequest(url, method, data, needToken);
  } else {
    return standardRequest(url, method, data, needToken);
  }
};
```

This approach allows all API methods to use the same interface regardless of the underlying implementation.

## Authentication Flow

Both request methods implement the same authentication flow:

1. **Token Retrieval**: Get token from either:
   - API configuration (`apiConfig.token`)
   - App global data (`getAppData().token`)

2. **Request Authorization**: Add token to requests that require authentication:
   ```javascript
   header.Authorization = `Bearer ${token}`;
   ```

3. **Error Handling**: Both methods handle unauthorized errors (401) the same way:
   - Clear tokens from storage and memory
   - Update application state
   - Notify the user
   - Reject the promise with an unauthorized error

## Configuration

### Standard Request Configuration

```javascript
api.init({
  baseUrl: 'http://localhost:3000/api',
  useCloudContainer: false
});
```

### Cloud Container Configuration

```javascript
api.init({
  useCloudContainer: true,
  envId: 'your-cloud-env-id',
  path: '/api'
});
```

### Dynamic Switching

You can switch between request methods at runtime:

```javascript
// Switch to cloud container
api.useCloudContainer(true, 'your-cloud-env-id', '/api');

// Switch back to standard request
api.useCloudContainer(false);
```

## Best Practices

1. **Development Configuration**:
   - Use `wx.request` (standard) during local development
   - Set `useCloudContainer: false` in your development environment

2. **Production Configuration**:
   - Use `wx.cloud.callContainer` in production
   - Set `useCloudContainer: true` with proper `envId` and `path`

3. **Environment Detection**:
   ```javascript
   // In app.js
   const envType = __wxConfig.envVersion;
   const isProduction = envType === 'release';
   
   api.init({
     baseUrl: isProduction ? '' : 'http://localhost:3000/api',
     useCloudContainer: isProduction,
     envId: isProduction ? 'your-cloud-env-id' : '',
     path: isProduction ? '/api' : ''
   });
   ```

4. **Token Handling**: Both methods use the same token management approach as described in the authentication documentation.

## Implementation Details

### Cloud Request Implementation

Our `cloudRequest` function is optimized for WeChat Cloud environments:

```javascript
const cloudRequest = (url, method, data, needToken = true) => {
  return new Promise((resolve, reject) => {
    // Prepare headers with authentication if needed
    const header = {};
    if (needToken) {
      const token = apiConfig.token || (getAppData() && getAppData().token);
      if (!token) {
        reject(new Error('No token available'));
        return;
      }
      header.Authorization = `Bearer ${token}`;
    }
    
    // Call cloud container
    wx.cloud.callContainer({
      config: {
        env: apiConfig.envId,
        path: `${apiConfig.path}${url}`,
      },
      header: header,
      method: method,
      data: data,
      success: res => {
        // Handle response including 401 unauthorized
        // ...
      },
      fail: err => reject(err)
    });
  });
};
```

## Integration with Existing Authentication System

This dual request system maintains complete compatibility with the existing authentication architecture described in `docs/authentication.md`:

1. **Token Storage**: Both methods use the same token storage approach
2. **App Instance**: The application still manages the full login flow
3. **Pages**: Pages continue to use `app.login()` for a consistent experience

## Troubleshooting

1. **Cloud Container Errors**:
   - Ensure your WeChat Cloud environment is properly configured
   - Verify the `envId` and `path` parameters are correct
   - Check cloud function access permissions

2. **Standard Request Errors**:
   - Verify your API server is running and accessible
   - Check the `baseUrl` configuration
   - Ensure CORS is properly configured on your development server

3. **Authentication Failures**:
   - Verify token expiration and validity
   - Check that token is being properly passed in request headers
   - Ensure backend token validation is working correctly 