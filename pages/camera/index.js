// Import the API module
const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    mealTime: '',
    timeValue: '',  // For the time picker in 24-hour format (HH:MM)
    timeUpdateInterval: null,
    isCameraActive: false,     // Whether the camera is in live view mode
    capturedImage: null,       // Path to the captured image
    pageVisible: true,         // Track if page is visible
    isSubscriptionActive: false, // Computed property for subscription status
    
    // Analysis related data
    analysisResult: null,      // The full analysis result from the API
    imageFileId: '',           // The cloud file ID of the uploaded image
    lastProcessedImage: null,  // Path to the last processed image (to avoid reprocessing)
    userComment: '',           // Added to track user comment input
    
    // Ingredient management related data
    editingIngredientId: null, // ID of the ingredient currently being edited inline
    hasPendingIngredients: false, // Whether there are ingredients with pending GI values
    
    // Task tracking for async processing
    taskId: null,
    taskStatus: null,
    taskPollingInterval: null,
    taskTimeoutTimer: null,    // Timer for task timeout
    taskProgress: 0,           // Progress percentage (0-100)
  },

  updateSubscriptionStatus: function() {
    // First set the current state from globalData
    this.setData({
      isSubscriptionActive: app.globalData.subscription.status === 'active'
    });
    
    // Then fetch the latest status from server
    app.fetchSubscriptionInfo().then(subscription => {
      this.setData({
        isSubscriptionActive: subscription.status === 'active'
      });
    }).catch(error => {
      console.error('Failed to fetch subscription status:', error);
      // On error, fallback to globalData (already set above)
    });
  },

  onLoad: function() {
    console.log('onLoad');
    
    // Initialize the meal time
    this.updateMealTime();
    
    // Set up interval to update time every minute
    this.data.timeUpdateInterval = setInterval(() => {
      this.updateMealTime();
    }, 60000); // 60000 ms = 1 minute
    
    // Initialize camera context but don't activate camera
    this.ctx = wx.createCameraContext();
    
    // Listen for app hide/show events
    wx.onAppHide(() => {
      console.log('App hidden - force deactivating camera');
      this.setData({ pageVisible: false });
      this.deactivateCamera();
    });
    
    wx.onAppShow(() => {
      console.log('App shown - updating page visibility');
      this.setData({ pageVisible: true });
      // Don't automatically activate camera
    });

    // Initialize subscription status
    this.updateSubscriptionStatus();
  },

  onUnload: function() {
    console.log('onUnload - cleaning up resources');
    
    // Clear the time update interval
    if (this.data.timeUpdateInterval) {
      clearInterval(this.data.timeUpdateInterval);
      this.data.timeUpdateInterval = null;
    }
    
    // Clear task polling interval and timeout timer if they exist
    if (this.data.taskPollingInterval) {
      clearInterval(this.data.taskPollingInterval);
    }
    if (this.data.taskTimeoutTimer) {
      clearTimeout(this.data.taskTimeoutTimer);
    }
    this.setData({
      taskPollingInterval: null,
      taskTimeoutTimer: null
    });
    
    // Force camera to be inactive immediately
    this.setData({
      isCameraActive: false
    });
    
    // Explicitly deactivate camera
    this.deactivateCamera();
    
    // Clear camera context
    this.ctx = null;
  },

  onHide: function() {
    // Called when navigating away from the page or switching tabs
    console.log('onHide - deactivating camera');
    
    // Force camera to be inactive immediately
    this.setData({
      isCameraActive: false,
      pageVisible: false
    });
    
    // Explicitly deactivate camera
    this.deactivateCamera();
    
    // Pause task polling and timeout timer if they exist
    if (this.data.taskPollingInterval) {
      clearInterval(this.data.taskPollingInterval);
    }
    if (this.data.taskTimeoutTimer) {
      clearTimeout(this.data.taskTimeoutTimer);
    }
    this.setData({
      taskPollingInterval: null,
      taskTimeoutTimer: null
    });
  },

  onShow: function() {
    console.log('onShow');
    this.setData({ pageVisible: true });
    this.updateMealTime();
    
    // Re-initialize camera context but don't activate camera automatically
    if (!this.ctx) {
      this.ctx = wx.createCameraContext();
    }
    
    // Resume task polling if we have an active task
    if (this.data.taskId && this.data.taskStatus && 
        (this.data.taskStatus === 'pending' || this.data.taskStatus === 'processing')) {
      this.startTaskPolling();
    }

    // Update subscription status
    this.updateSubscriptionStatus();
  },

  onReady: function() {
    console.log('onReady - camera page ready');
    // Camera context initialization if not already done
    if (!this.ctx) {
      this.ctx = wx.createCameraContext();
    }
  },

  // Update the meal time display
  updateMealTime: function() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const formattedHours = hours < 10 ? '0' + hours : hours;
    const formattedMinutes = minutes < 10 ? '0' + minutes : minutes;
    
    // Format time in 24-hour format (e.g., "15:45")
    const formattedTime = `${formattedHours}:${formattedMinutes}`;
    
    // The timeValue is already in 24-hour format
    const timeValue = `${formattedHours}:${formattedMinutes}`;
    
    this.setData({
      mealTime: formattedTime,
      timeValue: timeValue
    });
  },

  // Handle time picker change event
  bindTimeChange: function(e) {
    console.log('Time picker changed:', e.detail.value);
    
    // Stop the timer when a custom time is selected
    if (this.data.timeUpdateInterval) {
      clearInterval(this.data.timeUpdateInterval);
      this.data.timeUpdateInterval = null;
    }
    
    // The selected time is already in 24-hour format (HH:MM)
    const selectedTime = e.detail.value;
    
    this.setData({
      mealTime: selectedTime,
      timeValue: selectedTime
    });
  },

  // Handle camera errors
  error(e) {
    console.error('Camera error:', e.detail);
    wx.showToast({
      title: 'Camera error',
      icon: 'none'
    });
  },

  // Activate the camera live view
  activateCamera: function() {
    console.log('Activating camera - explicit user action');
    
    // Don't activate if page is not visible
    if (!this.data.pageVisible) {
      console.log('Page not visible, skipping camera activation');
      return;
    }
    
    // Initialize camera context if needed
    if (!this.ctx) {
      this.ctx = wx.createCameraContext();
    }
    
    // Set camera to active state
    this.setData({
      isCameraActive: true,
      capturedImage: null
    });
  },

  // Deactivate the camera
  deactivateCamera: function() {
    console.log('Deactivating camera - explicit cleanup');
    
    // Force camera to be inactive
    this.setData({
      isCameraActive: false
    });
    
    // Clear camera context if possible
    if (this.ctx) {
      // Some platforms might support stopping the camera explicitly
      if (typeof this.ctx.stopRecord === 'function') {
        try {
          this.ctx.stopRecord();
        } catch (e) {
          console.error('Error stopping camera:', e);
        }
      }
    }
  },

  // Capture a photo from the camera
  capturePhoto: function() {
    console.log('capturePhoto');
    
    if (!this.ctx) {
      console.error('Camera context not initialized');
      return;
    }

    this.ctx.takePhoto({
      quality: 'high',
      success: (res) => {
        console.log('Photo captured:', res.tempImagePath);
        
        this.setData({
          capturedImage: res.tempImagePath,
          lastProcessedImage: null, // Reset lastProcessedImage when a new image is captured
          isCameraActive: false
        });
        this.clearPageData();
      },
      fail: (err) => {
        console.error('Failed to capture photo:', err);
      }
    });
  },

  // Reset camera state (discard captured image)
  resetCamera: function() {
    this.setData({
      capturedImage: null,
      lastProcessedImage: null, // Reset lastProcessedImage
      isCameraActive: false
    });
    this.clearPageData();
  },

  // Take a photo using the camera (old method, now used to activate camera)
  takePhoto: function() {
    console.log('takePhoto - user explicitly activating camera');
    this.activateCamera();
  },

  // Open the system album/gallery
  openGallery: function() {
    wx.chooseImage({
      count: 1,
      sizeType: ['original', 'compressed'],
      sourceType: ['album'],
      success: (res) => {
        console.log('Selected image:', res.tempFilePaths[0]);
        
        // Display the selected image in the preview
        this.setData({
          capturedImage: res.tempFilePaths[0],
          lastProcessedImage: null, // Reset lastProcessedImage when a new image is selected
          isCameraActive: false
        });
        this.clearPageData();
      }
    });
  },
  
  // Analyze the image asynchronously
  analyzeImageAsync: function() {
    // Check if we have a captured image
    if (!this.data.capturedImage) {
      wx.showToast({
        title: '请先拍照或选择图片',
        icon: 'none'
      });
      return;
    }
    
    // Show loading indicator
    wx.showLoading({
      title: '准备分析...',
      mask: true
    });
    
    // Import required modules
    const image = require('../../utils/image.js');
    
    // Process the image
    (async () => {
      try {
        let fileID;
        
        // Check if we already have a cloud file ID for this image
        if (this.data.imageFileId && this.data.lastProcessedImage === this.data.capturedImage) {
          // Reuse the existing cloud file ID
          console.log('Reusing existing cloud file ID:', this.data.imageFileId);
          fileID = this.data.imageFileId;
          
          // Show a toast message to indicate we're reusing the existing file
          wx.showToast({
            title: '使用已上传的图片',
            icon: 'none',
            duration: 1500
          });
        } else {
          // Step 1: Resize the image
          const resizedImagePath = await image.resizeImage("resizeCanvas", this.data.capturedImage, this);
          console.log('Resized image path:', resizedImagePath);
          
          // Step 2: Upload the image to cloud storage
          // Generate timestamp and random number for unique filename
          const timestamp = Date.now();
          const randomNum = Math.floor(Math.random() * 100).toString().padStart(2, '0');
          
          // Get user openid from global data
          const userInfo = getApp().globalData.userInfo;
          if (!userInfo || !userInfo.openid) {
            throw new Error("User not logged in");
          }
          const openid = userInfo.openid;
          
          // Create cloud path in format: images/openid/year/month/hash.ext
          const now = new Date();
          const year = now.getFullYear();
          const month = String(now.getMonth() + 1).padStart(2, '0');
          const hash = `${timestamp}-${randomNum}`;
          const cloudPath = `images/${openid}/${year}/${month}/${hash}.jpg`;
          
          console.log('Uploading image:', cloudPath);
          
          // Upload the image
          const uploadResult = await wx.cloud.uploadFile({
            cloudPath,
            filePath: resizedImagePath,
            timeout: 10000 // 10 second timeout
          });
          
          if (!uploadResult || !uploadResult.fileID) {
            throw new Error('Failed to upload image to cloud');
          }
          console.log('Cloud upload result:', uploadResult);
          
          // Store the file ID
          fileID = uploadResult.fileID;
        }
        
        // Step 4: Call API to process the image asynchronously
        const taskResponse = await api.processImageAsync(fileID);
        console.log('Task response:', taskResponse);
        
        // Store the task ID, file ID, and the image path that was processed
        this.setData({
          taskId: taskResponse.id,
          taskStatus: taskResponse.status,
          imageFileId: fileID,
          lastProcessedImage: this.data.capturedImage, // Store the image path that was processed
          taskProgress: 0, // Initialize progress to 0
          hasPendingIngredients: false // Reset the hasPendingIngredients flag
        });
        
        // Start polling for task status
        this.startTaskPolling();
        
        // Update UI to show task is in progress - no need for toast message
        wx.hideLoading();
        
      } catch (error) {
        console.error('Error starting analysis:', error);
        wx.hideLoading();
        
        // Reset task state to remove processing UI
        this.setData({
          taskId: null,
          taskStatus: null,
          taskProgress: 0
        });
        
        wx.showToast({
          title: '启动分析失败，请重试',
          icon: 'none'
        });
      }
    })();
  },
  
  // Start polling for task status
  startTaskPolling: function() {
    // Clear any existing polling interval and timeout timer
    if (this.data.taskPollingInterval) {
      clearInterval(this.data.taskPollingInterval);
    }
    if (this.data.taskTimeoutTimer) {
      clearTimeout(this.data.taskTimeoutTimer);
    }
    
    // Set up timeout timer (30 seconds)
    const timeoutTimer = setTimeout(() => {
      console.log('Task polling timeout after 30 seconds');
      
      // Clear polling interval
      if (this.data.taskPollingInterval) {
        clearInterval(this.data.taskPollingInterval);
      }
      
      // Reset task state
      this.setData({
        taskPollingInterval: null,
        taskTimeoutTimer: null,
        taskId: null,
        taskStatus: null,
        taskProgress: 0
      });
      
      // Show timeout error message
      wx.showToast({
        title: '分析超时，请重试',
        icon: 'none',
        duration: 3000
      });
    }, 30000); // 30 seconds timeout
    
    // Set up polling interval (check every 2 seconds)
    const pollingInterval = setInterval(async () => {
      try {
        // Check task status
        const taskStatus = await api.getTaskStatus(this.data.taskId);
        console.log('Task status:', taskStatus);
        
        // Update task status in data
        this.setData({
          taskStatus: taskStatus.status
        });
        
        // If task is complete, stop polling and update UI
        if (taskStatus.status === 'completed') {
          clearInterval(pollingInterval);
          clearTimeout(timeoutTimer);
          
          // First set progress to 100%
          this.setData({
            taskProgress: 100
          });
          
          // Add a small delay before removing the processing state
          // This allows the progress bar to animate to 100% before disappearing
          setTimeout(() => {
            this.setData({
              taskPollingInterval: null,
              taskTimeoutTimer: null,
              taskId: null, // Clear taskId to remove processing state
              taskStatus: null // Clear taskStatus to remove processing state
            });
            
            // Update the analysis panel with the results
            this.updateAnalysisPanel(taskStatus.result, this.data.imageFileId);
            
            // Show success toast
            wx.showToast({
              title: '分析完成',
              icon: 'success'
            });
          }, 500); // 500ms delay for smooth transition
        } 
        // If task failed, stop polling and show error
        else if (taskStatus.status === 'failed') {
          clearInterval(pollingInterval);
          clearTimeout(timeoutTimer);
          this.setData({
            taskPollingInterval: null,
            taskTimeoutTimer: null,
            taskId: null, // Clear taskId to remove processing state
            taskStatus: null // Clear taskStatus to remove processing state
          });
          
          wx.showToast({
            title: '分析失败: ' + (taskStatus.error || '未知错误'),
            icon: 'none',
            duration: 3000
          });
        }
        // If task is still in progress, update progress indicator if available
        else if (taskStatus.status === 'processing' && taskStatus.progress !== undefined) {
          // Update progress bar - taskStatus.progress is already a percentage
          const progressPercentage = taskStatus.progress;
          this.setData({
            taskProgress: progressPercentage
          });
        }
      } catch (error) {
        console.error('Error checking task status:', error);
        // Don't stop polling on error, just log it
      }
    }, 2000);
    
    // Store the interval ID and timeout timer
    this.setData({
      taskPollingInterval: pollingInterval,
      taskTimeoutTimer: timeoutTimer,
      taskProgress: 0 // Reset progress when starting
    });
  },
  
  // New function to update the analysis panel with results
  updateAnalysisPanel: function(analysis, fileId) {
    console.log('Updating analysis panel with result:', analysis);
    
    // Map ingredients for debugging
    const mappedIngredients = (analysis.ingredients || []).map(ingredient => {
      console.log('Processing ingredient:', ingredient.name);
      
    //   // Determine GI category class
    //   ingredient.gi_category = 'gi-'+ingredient.gi_category;
      
    //   // Get portion value (numeric)
    //   const portion = ingredient.portion;
      
    //   // Generate a unique ID if not exists
      const id = ingredient.id || ('ingredient_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5));

    //   // Calculate nutrition values for this portion
    //   const carbs = ingredient.carbs_per_100g * portion / 100;
    //   const protein = ingredient.protein_per_100g * portion / 100;
    //   const fat = ingredient.fat_per_100g * portion / 100;
      
    //   const result = {
    //     ...ingredient,
    //     id: id,
    //     carbs: carbs,
    //     protein: protein,
    //     fat: fat,
    //     isPending: false,
    //     isLoading: false
    //   };
        return {
          ...ingredient,
          id: id,
        }
    });
    
    // Store the analysis result and file ID
    this.setData({
      analysisResult: {
        ...analysis,
        ingredients: mappedIngredients
      },
      imageFileId: fileId,
      // Reset the hasPendingIngredients flag
      hasPendingIngredients: false
    });
    
    // Always calculate total GL from the ingredients list
    // this.calculateTotalGl();
    
    // Scroll to the analysis panel
    wx.createSelectorQuery()
      .select('#analysis-panel')
      .boundingClientRect(function(rect){
        wx.pageScrollTo({
          scrollTop: rect.top,
          duration: 300
        });
      })
      .exec();
  },
  
  // Add a function to record the meal
  recordMeal: function() {
    if (!this.data.analysisResult || !this.data.imageFileId) {
      wx.showToast({
        title: '请先分析餐食',
        icon: 'none'
      });
      return;
    }
    
    // Show loading indicator
    wx.showLoading({
      title: '正在记录...',
    });
    
    // Prepare ingredients data with updated nutrition information
    // console.log('this.data.ingredientsList', this.data.ingredientsList);
    // const ingredients = this.data.ingredientsList.map(ingredient => {
    //   // Calculate GL for this ingredient
    //   // the ingredient.carbs is per_100g. TODO: we need to fix this
    //   const portion = ingredient.portion || 0;
    //   const carbsInPortion = (ingredient.carbs * portion) / 100;
    //   const gl = (ingredient.gi * carbsInPortion) / 100;
      
    //   return {
    //     name: ingredient.name,
    //     portion: ingredient.portion,
    //     gi: ingredient.gi,
    //     gi_category: ingredient.giCategoryClass === 'gi-low' ? 'low' : 
    //                  ingredient.giCategoryClass === 'gi-medium' ? 'medium' : 'high',
    //     carbs_per_100g: ingredient.carbs,
    //     protein_per_100g: ingredient.protein,
    //     fat_per_100g: ingredient.fat,
    //     gl: gl
    //   };
    // });
    const meal_data = {
      "analysis": {
        ...this.data.analysisResult,
        "meal_time": this.convertToUTC(this.data.mealTime),
      },
      "file_id": this.data.imageFileId,
    }
    console.log('meal_data', meal_data);
    api.saveMeal(meal_data).then(res => {
      wx.hideLoading();
      wx.showToast({
        title: '餐食记录成功！',
        icon: 'success',
        duration: 2000,
        success: () => {
          this.resetCamera();
          // After 2 seconds, go back to dashboard
          setTimeout(() => {
            const app = getApp();
            app.globalData.needRefresh = true;
            wx.switchTab({
              url: '/pages/dashboard/index'
            });
          }, 2000);
        }
      });
    }).catch(err => {
      console.error('Error recording meal:', err);
      wx.hideLoading();
      wx.showToast({
        title: '记录失败，请重试',
        icon: 'none'
      });
    });
  },

  // New function to handle user comment input
  onCommentInput: function(e) {
    this.setData({
      userComment: e.detail.value
    });
  },
  
  // Function to submit reanalysis request based on user edits
  onSubmitComment: async function() {
    // Don't do anything if already processing
    if (this.data.taskId && (this.data.taskStatus === 'pending' || this.data.taskStatus === 'processing')) {
      return;
    }
    
    try {
      // Compare current ingredients with original analysis to detect changes
      const currentIngredients = this.data.analysisResult.ingredients || [];

      // Create a simpler feedback comment that instructs the LLM to complete nutrition for new ingredients
      let feedback = '以下是用户确认的食材列表：\n';
      
      // List all current ingredients with their portions
      currentIngredients.forEach((ing, index) => {
        feedback += `${index + 1}. ${ing.name}: ${ing.portion}克\n`;
      });
            
      // Add clear instructions for the LLM
      feedback += '\n请保留用户列出的所有食材，并为新添加的食材补充营养信息（碳水、蛋白质、脂肪）和GL值。请勿添加或删除任何食材。';
      
      console.log('Feedback for LLM:', feedback);
            
      // Call API to process image asynchronously with the feedback
      const taskResponse = await api.processImageAsync(
        this.data.imageFileId,
        null, // Only send the modified ingredients list
        feedback // Send feedback based on user edits
      );
      
      console.log('Task response:', taskResponse);
      
      // Store the task ID and status
      this.setData({
        taskId: taskResponse.id,
        taskStatus: taskResponse.status,
        taskProgress: 0, // Initialize progress to 0
        hasPendingIngredients: false // Reset the hasPendingIngredients flag
      });
      
      // Start polling for task status
      this.startTaskPolling();
      
    } catch (err) {
      console.error('Error reprocessing image:', err);
      wx.showToast({
        title: '重新分析失败，请重试',
        icon: 'none'
      });
    }
  },

  // ==========================================
  // Ingredient Management Functions
  // ==========================================
  
  // Show the add ingredient panel
  addNewIngredient: function() {
    // Create a new ingredient with a unique ID and add it directly to the list
    const newIngredientId = 'custom_' + Date.now();

    const newIngredient = {
      id: newIngredientId,
      name: '',
      portion: 0,           // Numeric value (0) instead of empty string
      gi: 'pending',        // Keep as 'pending' for GI
      giCategoryClass: 'gi-pending',
      carbs: 0,             // Numeric value (0) instead of empty string
      protein: 0,           // Numeric value (0) instead of empty string
      fat: 0,               // Numeric value (0) instead of empty string
      carbsPer100g: 0,
      proteinPer100g: 0,
      fatPer100g: 0,
      isPending: true,
      isLoading: false,
      isNew: true  // Flag to indicate this is a new row being edited
    }
    
    // Add to ingredients list with empty fields for user to edit
    let updatedList = [];
    if (this.data.analysisResult && this.data.analysisResult.ingredients) {
      updatedList = [...this.data.analysisResult.ingredients, newIngredient];
    } else {
      updatedList = [newIngredient];
    }
    
    console.log('updatedList', updatedList);
    this.setData({
      analysisResult: {
        ...this.data.analysisResult,
        ingredients: updatedList
      },
      editingIngredientId: newIngredientId, // Set this ingredient as being edited
      hasPendingIngredients: true // Set the hasPendingIngredients flag
    });
    
    // Update total GL
    this.calculateTotalGl();
  },
  
  // Edit ingredient portion
  editIngredientPortion: function(e) {
    const id = e.currentTarget.dataset.ingredientId;
    
    this.setData({
      editingIngredientId: id
    });
  },
  
  // Delete ingredient
  deleteIngredient: function(e) {
    const id = e.currentTarget.dataset.ingredientId;
    console.log('Deleting ingredient with ID:', id);
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个食材吗？',
      success: (res) => {
        if (res.confirm) {
          // Get the ingredient being deleted for logging
          const deletedIngredient = this.data.analysisResult.ingredients.find(item => item.id === id);
          console.log('Deleted ingredient:', deletedIngredient);
          
          // Filter out the ingredient with the given ID
          const updatedList = this.data.analysisResult.ingredients.filter(item => item.id !== id);
          console.log('Updated list has', updatedList.length, 'ingredients');
          
          this.setData({
            analysisResult: {
              ...this.data.analysisResult,
              ingredients: updatedList
            },
            hasPendingIngredients: true // Set the hasPendingIngredients flag
          });
          
          console.log('Before recalculating, current total GL:', this.data.analysisResult.totalGl);
          
          // Recalculate total GL from the ingredients list
          this.calculateTotalGl();
          
          console.log('After recalculating, new total GL:', this.data.analysisResult.totalGl);
        }
      }
    });
  },
  
  // Calculate total GL value
  calculateTotalGl: function() {
    const ingredients = this.data.analysisResult.ingredients;
    let totalGl = 0;
    let totalCarbs = 0;
    let totalProtein = 0;
    let totalFat = 0;
    let hasPendingIngredients = false;
    
    console.log('Calculating total GL for', ingredients.length, 'ingredients');
    
    // If we're currently processing, don't update the GL value
    if (this.data.taskId && (this.data.taskStatus === 'pending' || this.data.taskStatus === 'processing')) {
      console.log('Task is processing, not updating GL value');
      this.setData({
        hasPendingIngredients: true
      });
      return;
    }
    
    // Calculate GL for each ingredient
    ingredients.forEach(ingredient => {
      console.log('ingredient', ingredient);
      // Check if this ingredient needs analysis (missing GI or nutrition data)
      if ( ingredient.gi === 'pending' || ingredient.isPending || 
          ingredient.gi === undefined || ingredient.gi === null) {
        console.log('Ingredient needs analysis:', ingredient);
        hasPendingIngredients = true;
        return;
      }

      // Calculate GL based on carbs, GI, and portion
      const gl = ingredient.carbs_per_100g * ingredient.portion / 100 * ingredient.gi / 100;
      totalGl += gl;
      console.log('totalGl', totalGl);
      
      totalCarbs += ingredient.carbs_per_100g * ingredient.portion / 100;
      totalProtein += ingredient.protein_per_100g * ingredient.portion / 100;
      totalFat += ingredient.fat_per_100g * ingredient.portion / 100;
      
    });
    
    console.log('hasPendingIngredients: ', hasPendingIngredients);
    // Round to 1 decimal place
    totalGl = Math.round(totalGl * 10) / 10;
    totalCarbs = Math.round(totalCarbs * 10) / 10;
    totalProtein = Math.round(totalProtein * 10) / 10;
    totalFat = Math.round(totalFat * 10) / 10;
    
    console.log('Final total GL:', totalGl);
    
    // Determine GL class
    let totalGlClass = 'gl-low';
    if (totalGl > 20) {
      totalGlClass = 'gl-high';
    } else if (totalGl > 10) {
      totalGlClass = 'gl-medium';
    }

    // update analysisResult
    this.setData({
      analysisResult: {
        ...this.data.analysisResult,
        total_gl: hasPendingIngredients ? '需要重新分析' : totalGl,
        totalGlClass: hasPendingIngredients ? 'gl-pending' : totalGlClass,
        total_carbs: totalCarbs,
        total_protein: totalProtein,
        total_fat: totalFat
      },
      hasPendingIngredients: hasPendingIngredients
    });
  },

  clearPageData: function() {
    this.setData({
      analysisResult: null,
      editingIngredientId: null,
      hasPendingIngredients: false
    });
  },

  // Convert local time (HH:MM) to UTC ISO format
  convertToUTC: function(localTime, customDate = null) {
    // Parse the time string (format: "HH:MM")
    const [hours, minutes] = localTime.split(':').map(Number);
    
    // Create a Date object for today or the specified date with the specified time
    const date = customDate || new Date();
    date.setHours(hours, minutes, 0, 0); // Set hours and minutes, reset seconds and milliseconds
    
    // Convert to ISO string which is in UTC format
    const utcTime = date.toISOString();
    
    console.log(`Converting local time ${localTime} to UTC: ${utcTime}`);
    
    return utcTime;
  },

  // Update ingredient name directly in the list
  updateIngredientName: function(e) {
    const id = e.currentTarget.dataset.ingredientId;
    const newName = e.detail.value;
    
    // Find the ingredient in the list and update its name while preserving other properties
    console.log('this.data.analysisResult.ingredients', this.data.analysisResult.ingredients);
    const updatedList = this.data.analysisResult.ingredients.map(item => {
      if (item.id === id) {
        return { ...item, name: newName }; // Preserve isNew flag and other properties
      }
      return item;
    });
    
    this.setData({
      analysisResult: {
        ...this.data.analysisResult,
        ingredients: updatedList
      }
    });

    // Note: Nutrition info will be updated when the user submits for reanalysis
  },
  
  // Helper to update portion and gl for an ingredient by id
  updateIngredientPortionById: function(id, newPortion) {
    // Ensure value is not negative
    let portion = Math.max(0, parseInt(newPortion) || 0);
    const updatedList = (this.data.analysisResult.ingredients || []).map(item => {
      if (item.id === id) {
        return {
          ...item,
          portion: portion,
          gl: portion * item.carbs_per_100g / 100.0 * item.gi / 100
        };
      }
      return item;
    });
    this.setData({
      analysisResult: {
        ...this.data.analysisResult,
        ingredients: updatedList
      }
    });
    this.calculateTotalGl();
  },
  
  // Update ingredient portion value (numeric)
  updateIngredientPortionValue: function(e) {
    const id = e.currentTarget.dataset.ingredientId;
    let newValue = parseInt(e.detail.value) || 0;
    this.updateIngredientPortionById(id, newValue);
  },
  
  // Decrease portion by 10g
  decreasePortionInline: function(e) {
    console.log('decreasePortionInline called with event:', e);
    const id = e.currentTarget.dataset.ingredientId;
    const ingredient = (this.data.analysisResult.ingredients || []).find(item => item.id === id);
    console.log('Current ingredient:', ingredient);
    if (!ingredient) {
      console.error('Ingredient not found with ID:', id);
      return;
    }
    let newValue = Math.max(0, (ingredient.portion || 0) - 10);
    console.log('New portion value:', newValue);
    this.updateIngredientPortionById(id, newValue);
  },
  
  // Increase portion by 10g
  increasePortionInline: function(e) {
    console.log('increasePortionInline called with event:', e);
    const id = e.currentTarget.dataset.ingredientId;
    const ingredient = (this.data.analysisResult.ingredients || []).find(item => item.id === id);
    console.log('Current ingredient:', ingredient);
    if (!ingredient) {
      console.error('Ingredient not found with ID:', id);
      return;
    }
    let newValue = (ingredient.portion || 0) + 10;
    console.log('New portion value:', newValue);
    this.updateIngredientPortionById(id, newValue);
  },
  
  // Finish editing portion (called on blur)
  finishEditingPortion: function(e) {
    const id = e.currentTarget.dataset.ingredientId;
    console.log('Finishing editing for ingredient ID:', id);
    
    // Find the ingredient in the list
    const ingredient = this.data.analysisResult.ingredients.find(item => item.id === id);
    
    // If the ingredient name is empty, don't finish editing
    if (ingredient && ingredient.isNew && (!ingredient.name || ingredient.name.trim() === '')) {
      console.log('Ingredient name is empty, not finishing editing');
      return;
    }
    
    // Find the ingredient in the list and remove isNew flag if it exists
    const updatedList = this.data.analysisResult.ingredients.map(item => {
      if (item.id === id) {
        console.log('Removing isNew flag from ingredient:', item.name);
        
        // If this was a new ingredient, set a default portion value
        if (item.isNew) {
          return { 
            ...item, 
            isNew: false, // Remove the isNew flag
            portion: 100 // Set default portion to 100g as a number
          };
        } else {
          return { 
            ...item, 
            isNew: false // Remove the isNew flag
          };
        }
      }
      return item;
    });
    
    // Exit edit mode by clearing the editingIngredientId and updating the list
    this.setData({
      analysisResult: {
        ...this.data.analysisResult,
        ingredients: updatedList
      },
      editingIngredientId: null
    });
    
    // Update total GL
    this.calculateTotalGl();
  },

  showSubscriptionRequired: function() {
    wx.showModal({
      title: '需要订阅',
      content: '此功能需要有效的会员订阅。是否立即订阅？',
      confirmText: '立即订阅',
      cancelText: '暂不订阅',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({
            url: '/pages/subscription/index'
          });
        }
      }
    });
  },
}) 