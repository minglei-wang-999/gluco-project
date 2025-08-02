const api = require('../../utils/api.js');
const image = require('../../utils/image.js');
const app = getApp();

Page({
  data: {
    logStep: 1, // Step 1: Capture, Step 2: Review, Step 3: Confirm
    currentPhoto: '',
    tempImagePath: '',
    imageFileId: '',
    isLoading: false,
    cameraActive: true, // Add flag to track camera state
    analysis: null,
    userComment: '', // Added to track user comment input
    // Mock data for meal analysis
    mockAnalysis: {
      ingredients: [
        { name: "米饭 (1 杯)", portion: 1, gi: 72, carbs: 45, protein: 4, fat: 0, gi_category: "high", gl: 32, gl_category: "medium" },
        { name: "鸡肉 (3盎司)", portion: 1, gi: 0, carbs: 0, protein: 26, fat: 3, gi_category: "low", gl: 0, gl_category: "low" },
        { name: "西兰花", portion: 1, gi: 15, carbs: 6, protein: 3, fat: 0, gi_category: "low", gl: 1, gl_category: "low" },
        { name: "酱汁", portion: 1, gi: 30, carbs: 5, protein: 0, fat: 2, gi_category: "low", gl: 1, gl_category: "low" }
      ],
      notes: "白米饭配鸡肉和蔬菜",
      total_carbs: 56,
      total_protein: 33,
      total_fat: 5,
      total_gl: 34,
      meal_gl_category: "medium",
      impact_level: "moderate",
      protein_level: "good",
      fat_level: "low",
      impact_explanation: "这顿饭的血糖负荷中等，主要来自白米饭。",
      best_time: "中午或体育活动前",
      tips: [
        "考虑将白米饭换成糙米或藜麦，以降低整体GL值。",
        "添加更多蔬菜可以进一步平衡餐食。",
        "这种蛋白质含量有助于控制血糖反应。"
      ]
    }
  },

  onLoad: function () {
    // Check if user is logged in
    const app = getApp();
    if (!app.globalData.isLogin) {
      app.login((success) => {
        if (!success) {
          wx.showToast({
            title: '登录失败，请重试',
            icon: 'none'
          });
        }
      });
      }
  },
    
  onTakePhoto: function() {
    const ctx = wx.createCameraContext();
    ctx.takePhoto({
      quality: 'high',
      success: (res) => {
        this.setData({
          currentPhoto: res.tempImagePath,
          logStep: 2,
          cameraActive: false // Explicitly disable camera
        });
        this.analyzePhoto(res.tempImagePath);
      },
      fail: (err) => {
        wx.showToast({
          title: '拍照失败',
          icon: 'none'
        });
        console.error('Camera error:', err);
      }
    });
  },
  
  onChooseFromLibrary: function() {
    // Ensure camera is disabled before showing image picker
    this.setData({ cameraActive: false });
    
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album'],
      success: (res) => {
        this.setData({
          currentPhoto: res.tempFilePaths[0],
          logStep: 2
        });
        // wait 1 second before analyzing 
        Promise.resolve(this.analyzePhoto(res.tempFilePaths[0])).then(() => {
          this.setData({ isLoading: false });
        });
      },
      fail: (err) => {
        console.error('Image picker error:', err);
        this.setData({ 
          cameraActive: true
         });
      }
    });
  },
  
  onCommentInput: function(e) {
    this.setData({
      userComment: e.detail.value
    });
  },
  
  onSubmitComment: async function() {
    if (!this.data.userComment.trim()) {
      wx.showToast({
        title: '请输入您的修改建议',
        icon: 'none'
      });
      return;
    }
    console.log('userComment', this.data.userComment);
    this.setData({ isLoading: true });
    
    // Call API to reprocess image with user comment
    try {
      await api.processImage(
        this.data.imageFileId,
        this.data.analysis,
        this.data.userComment
      ).then((res) => {
        console.log(res);
        this.setData({
          isLoading: false,
          analysis: res,
          userComment: ''
        });
      }).catch((err) => {
        console.error(err);
      });
    } catch(err) {
      console.error(err);
    } finally {
      this.setData({
        isLoading: false
      });
    }
  },
  
  analyzePhoto: async function(filePath) {
    if (this.data.isLoading || this.data.logStep !== 2 || !filePath) {
      return;
    }

    this.setData({ isLoading: true });

    try {
      if (!this.data.imageFileId) {
        console.log('resizing image');
        
        // Await the resizing of the image
        const resizedImagePath = await image.resizeImage("resizeCanvas", filePath);
        console.log('resized image:', resizedImagePath);

        // Get file extension from the temp path
        const ext = 'jpg'; // We're converting to JPG in resizeImage

        // Generate timestamp and random number
        const timestamp = Date.now();
        const randomNum = Math.floor(Math.random() * 100).toString().padStart(2, '0');

        // Get user openid from global data
        const userInfo = app.globalData.userInfo;
        if (!userInfo || !userInfo.openid) {
          throw new Error("User not logged in");
        }
        const openid = userInfo.openid;

        // Create cloud path in format: images/openid/year/month/hash.ext
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const hash = `${timestamp}-${randomNum}`;
        const cloudPath = `images/${openid}/${year}/${month}/${hash}.${ext}`;

        console.log('uploading image:', cloudPath);
        
        // Add timeout and retry logic for upload
        let retryCount = 0;
        const maxRetries = 2;
        let uploadResult;
        
        while (retryCount <= maxRetries) {
          try {
            console.log(`Upload attempt ${retryCount + 1}`);
            uploadResult = await wx.cloud.uploadFile({
              cloudPath,
              filePath: resizedImagePath,
              timeout: 10000 // 10 second timeout
            });
            if (uploadResult.fileID) {
              console.log('Upload successful on attempt', retryCount + 1);
              break; // Success, exit the retry loop
            }
          } catch (uploadErr) {
            console.error(`Upload attempt ${retryCount + 1} failed:`, uploadErr);
            if (retryCount >= maxRetries) throw uploadErr;
            retryCount++;
            // Wait before retry (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
          }
        }
        
        if (!uploadResult || !uploadResult.fileID) {
          throw new Error('Failed to upload image to cloud after retries');
        }
        console.log('Cloud upload result:', uploadResult);

        this.setData({
          imageFileId: uploadResult.fileID
        });
      }
      // get download url
      const downloadUrl = await wx.cloud.getTempFileURL({
        fileList: [{
          "fileID": this.data.imageFileId,
          "maxAge": 60 * 60 // 1 hour
        }]
      });
      console.log('Download URL:', downloadUrl);

      // call api to process image
      await api.processImage(downloadUrl.fileList[0].tempFileURL).then((res) => {
        console.log(res);
        this.setData({
          isLoading: false,
          analysis: res
        });
      }).catch((err) => {
        console.error(err);
      });
    } catch (err) {
      console.error(err);
    } finally {
      this.setData({
        isLoading: false
      });
    }
  },
  
  onBack: function() {
    if (this.data.logStep > 1) {
      // If going back to camera view, re-enable camera
      if (this.data.logStep === 2) {
        this.setData({
          logStep: 1,
          cameraActive: true
        });
      } else {
        this.setData({
          logStep: this.data.logStep - 1
        });
      }
    }
  },
  
  onNextStep: function() {
    const nextStep = this.data.logStep + 1;
    this.setData({
      logStep: nextStep
    });
    
    if (nextStep === 3) {
      // In a real app, this would save the meal data to server
      api.saveMeal(
        {
          analysis: this.data.analysis,
          file_id: this.data.imageFileId
        }
      ).then((res) => {
        wx.showToast({
          title: '餐食记录成功！',
          icon: 'success',
          duration: 2000,
          success: () => {
            // After 2 seconds, go back to dashboard
            setTimeout(() => {
              this.setData({ logStep: 1 });
              app.globalData.needRefresh = true;
              wx.switchTab({
                url: '/pages/dashboard/index'
              });
            }, 2000);
          }
        });
      }).catch((err) => {
        console.error(err);
      });
    }
  },
  
  onFinish: function() {
    // In a real app, this would be called after saving meal data
    this.setData({ logStep: 1 });
    wx.switchTab({
      url: '/pages/dashboard/index'
    });
  },
  
  getHeaderTitle: function() {
    switch(this.data.logStep) {
      case 1: return "拍摄餐食";
      case 2: return "餐食分析";
      case 3: return "餐食已记录";
      default: return "记录餐食";
    }
  }
}); 