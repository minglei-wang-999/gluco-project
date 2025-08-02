const util = require('../../utils/util.js');
const api = require('../../utils/api.js');

Page({
  data: {
    isLoading: true,
    today: '',
    selectedDate: null,
    isCurrentDateToday: true,
    currentGL: 0,
    dailyGoal: 100,
    stabilityScore: 0,
    hourlyData: [],
    percentComplete: 0,
    meals: [],
    // For refresh hint
    showRefreshHint: true,
    // For meal detail modal
    showMealDetail: false,
    selectedMeal: null,
    // Mock data initially
    mockData: {
      currentGL: 68,
      dailyGoal: 100,
      stabilityScore: 82,
      meals: [
        { id: 1, name: "早餐", time: "7:30 AM", gl: 22, items: "燕麦粥, 蓝莓, 杏仁奶", hasDistributionIssue: false },
        { id: 2, name: "午餐", time: "12:15 PM", gl: 35, items: "鸡肉沙拉, 全麦面包, 苹果", hasDistributionIssue: true },
        { id: 3, name: "零食", time: "3:30 PM", gl: 11, items: "希腊酸奶, 核桃", hasDistributionIssue: false }
      ],
      hourlyData: [
        {hour: 6, gl: 0}, {hour: 7, gl: 20}, {hour: 8, gl: 2}, 
        {hour: 9, gl: 0}, {hour: 10, gl: 0}, {hour: 11, gl: 0}, 
        {hour: 12, gl: 30}, {hour: 13, gl: 5}, {hour: 14, gl: 0},
        {hour: 15, gl: 11}, {hour: 16, gl: 0}, {hour: 17, gl: 0},
        {hour: 18, gl: 0}, {hour: 19, gl: 0}, {hour: 20, gl: 0},
        {hour: 21, gl: 0}, {hour: 22, gl: 0}, {hour: 23, gl: 0}
      ]
    }
  },
  
  onLoad: function () {
    // Initialize with today's date
    const now = new Date();
    const formattedDate = util.formatDateFull(now);
    
    this.setData({
      today: formattedDate,
      selectedDate: now,
      isCurrentDateToday: true
    });
    
    // Check if user is logged in
    const app = getApp();
    if (!app.globalData.token) {
      // Redirect to login page if not logged in
      wx.redirectTo({
        url: '/pages/login/index'
      });
      return;
    }
    
    // Check if refresh hint should be shown
    this.checkRefreshHintPreference();
    
    // For now use mock data but set up for real data later
    // this.setupMockData();
    
    // Will use this later to fetch real data
    this.fetchDailyData(now);
  },
  
  // Check user preference for refresh hint from storage
  checkRefreshHintPreference: function() {
    wx.getStorage({
      key: 'hideRefreshHint',
      success: (res) => {
        if (res.data === true) {
          this.setData({
            showRefreshHint: false
          });
        }
      },
      fail: () => {
        // If no preference is stored, show the hint by default
        this.setData({
          showRefreshHint: true
        });
      }
    });
  },
  
  // Handle dismissal of refresh hint
  dismissRefreshHint: function() {
    this.setData({
      showRefreshHint: false
    });
    
    // Save user preference to storage
    wx.setStorage({
      key: 'hideRefreshHint',
      data: true
    });
  },
  
  onShow: function () {
    // Refresh data when returning to this page
    // For now we'll just use mock data
    const app = getApp();
    if (app.globalData.needRefresh) {
      this.fetchDailyData();
      app.globalData.needRefresh = false;
    }
  },
  
  setupMockData: function() {
    const mockData = this.data.mockData;
    
    // Add GL colors to meals
    const meals = mockData.meals.map(meal => {
      meal.glCategory = meal.totalGl > 20 ? 'high' : (meal.totalGl > 10 ? 'medium' : 'low');
      return meal;
    });
    
    // Calculate percent complete
    const percentComplete = (mockData.currentGL / mockData.dailyGoal) * 100;
    
    this.setData({
      currentGL: mockData.currentGL,
      dailyGoal: mockData.dailyGoal,
      stabilityScore: mockData.stabilityScore,
      stabilityColor: util.getStabilityColor(mockData.stabilityScore),
      hourlyData: mockData.hourlyData,
      percentComplete: percentComplete,
      meals: meals,
      isLoading: false
    });
  },
  
  fetchDailyData: function(date) {
    // This will be implemented later to fetch real data from API
    this.setData({ isLoading: true });
    
    // Example implementation:
    const targetDate = date || this.data.selectedDate || new Date();
    const startTime = new Date(new Date(targetDate).setHours(0, 0, 0, 0)).toISOString();
    const endTime = new Date(new Date(targetDate).setHours(23, 59, 59, 999)).toISOString();
    
    return new Promise((resolve, reject) => {
      api.getMealHistory(startTime, endTime)
        .then(data => {
          console.log('data', data);
          const meals = data.map(meal => util.snakeToCamel(meal));
          // Transform API data to UI format
          console.log('meals', meals);
          // Format meals data
          const processedMeals = meals.map(meal => {
            const mealTime = new Date(meal.mealTime+"Z");
            return {
              id: meal.id,
              name: util.getMealType(mealTime),
              time: util.formatTimeAMPM(mealTime),
              totalGl: meal.totalGl,
              glCategory: meal.totalGl > 20 ? 'high' : (meal.totalGl > 10 ? 'medium' : 'low'),
              items: meal.ingredients.map(ingredient => ingredient.name).join(', '),
              hasDistributionIssue: false,
              imageUrl: meal.imageUrl,
              // Add additional fields for meal detail view
              totalCarbs: meal.totalCarbs || 0,
              totalProtein: meal.totalProtein || 0,
              totalFat: meal.totalFat || 0,
              notes: meal.notes || '',
              ingredients: meal.ingredients.map(ingredient => ({
                ...ingredient,
                carbs: ingredient.carbsPer_100g * ingredient.portion / 100.0 || 0,
                protein: ingredient.proteinPer_100g * ingredient.portion / 100.0 || 0,
                fat: ingredient.fatPer_100g * ingredient.portion / 100.0 || 0
              }))
            };
          });
          
          // Calculate daily metrics
          let sum = 0;
          meals.forEach(meal => {
            sum += meal.totalGl || 0;
          });
          const currentGL = Math.round(sum);
          console.log('currentGL', currentGL);

          // Initialize hourly data array for 6am to 12am (19 hours)
          const hourlyData = Array(19).fill().map(() => ({gl: 0}));
          
          // Aggregate GL values by hour, handling edge cases
          meals.forEach(meal => {
            const mealTime = new Date(meal.mealTime+"Z");
            let hour = mealTime.getHours();
            
            // Adjust hours before 6am to 6am bucket
            if (hour < 6) {
              hour = 6;
            }
            // Adjust hours after midnight to midnight bucket
            else if (hour > 24) {
              hour = 24;
            }
            
            // Map 6am-12am to 0-18 index
            const index = Math.min(hour - 6, 18);
            hourlyData[index].gl += Math.round(meal.totalGl || 0);
            hourlyData[index].hour = hour;
          });
          console.log('processedMeals', processedMeals);
          this.setData({
            currentGL: currentGL,
            dailyGoal: 100,
            stabilityScore: 82,
            stabilityColor: util.getStabilityColor(82),
            hourlyData: hourlyData,
            percentComplete: 82,
            meals: processedMeals,
            isLoading: false
          });
          
          resolve(); // Resolve the promise when data is loaded
        })
        .catch(err => {
          console.error('Error fetching daily data:', err);
          this.setData({ isLoading: false });
          wx.showToast({
            title: '获取数据失败',
            icon: 'none'
          });
          
          reject(err); // Reject the promise on error
        });
    });
  },
  
  onPrevDay: function() {
    // Get the current displayed date
    const selectedDate = new Date(this.data.selectedDate);
    
    // Subtract one day
    selectedDate.setDate(selectedDate.getDate() - 1);
    
    // Format the date for display
    const formattedDate = util.formatDateFull(selectedDate);
    
    // Check if the new date is today
    const today = new Date();
    const isCurrentDateToday = 
      selectedDate.getDate() === today.getDate() && 
      selectedDate.getMonth() === today.getMonth() && 
      selectedDate.getFullYear() === today.getFullYear();
    
    // Update the UI
    this.setData({
      selectedDate: selectedDate,
      today: formattedDate,
      isCurrentDateToday: isCurrentDateToday
    });
    
    // Show loading indicator
    wx.showLoading({
      title: '加载中...',
    });
    
    // Fetch data for the new date
    this.fetchDailyData(selectedDate)
      .then(() => {
        wx.hideLoading();
      })
      .catch(err => {
        wx.hideLoading();
        wx.showToast({
          title: '获取数据失败',
          icon: 'none'
        });
      });
  },
  
  onNextDay: function() {
    // Only proceed if not already on today's date
    if (this.data.isCurrentDateToday) {
      return;
    }
    
    // Get the current displayed date
    const selectedDate = new Date(this.data.selectedDate);
    
    // Add one day
    selectedDate.setDate(selectedDate.getDate() + 1);
    
    // Format the date for display
    const formattedDate = util.formatDateFull(selectedDate);
    
    // Check if the new date is today
    const today = new Date();
    const isCurrentDateToday = 
      selectedDate.getDate() === today.getDate() && 
      selectedDate.getMonth() === today.getMonth() && 
      selectedDate.getFullYear() === today.getFullYear();
    
    // Update the UI
    this.setData({
      selectedDate: selectedDate,
      today: formattedDate,
      isCurrentDateToday: isCurrentDateToday
    });
    
    // Show loading indicator
    wx.showLoading({
      title: '加载中...',
    });
    
    console.log('selectedDate', selectedDate);
    // Fetch data for the new date
    this.fetchDailyData(selectedDate)
      .then(() => {
        wx.hideLoading();
      })
      .catch(err => {
        wx.hideLoading();
        wx.showToast({
          title: '获取数据失败',
          icon: 'none'
        });
      });
  },
  
  onTapMeal: function(e) {
    const meal = e.detail.meal;
    
    // Instead of fetching from API, use the existing meal data
    const mealDetail = {
      id: meal.id,
      name: meal.name,
      time: meal.time,
      totalGl: meal.totalGl,
      glCategory: meal.totalGl > 20 ? 'high' : (meal.totalGl > 10 ? 'medium' : 'low'),
      totalCarbs: meal.totalCarbs || 0,
      totalProtein: meal.totalProtein || 0,
      totalFat: meal.totalFat || 0,
      notes: meal.notes || '无备注',
      imageUrl: meal.imageUrl,
      ingredients: meal.ingredients || []
    };
    console.log('mealDetail', mealDetail);
    this.setData({
      selectedMeal: mealDetail,
      showMealDetail: true
    });
  },
  
  closeMealDetail: function() {
    this.setData({
      showMealDetail: false,
      selectedMeal: null
    });
  },
  
  onTapAddMeal: function() {
    wx.switchTab({
      url: '/pages/camera/index'
    });
  },
  
  onViewHistory: function() {
    // Navigate to the report/history tab
    wx.switchTab({
      url: '/pages/reports/index'
    });
  },
  
  onShareMeal: function() {
    // Navigate to poster page with meal data
    const meal = this.data.selectedMeal;
    wx.navigateTo({
      url: `/pages/poster/index?mealData=${encodeURIComponent(JSON.stringify({
        name: meal.name,
        image: meal.imageUrl,
        gl: meal.totalGl,
        fat: meal.totalFat,
        protein: meal.totalProtein,
        carbs: meal.totalCarbs,
        description: meal.notes || '',
      }))}`
    });
  },
  
  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh: function() {
    console.log('Pull down refresh triggered');
    console.log('selectedDate', this.data.selectedDate);
    // Fetch fresh data for the currently displayed date
    this.fetchDailyData(this.data.selectedDate)
      .then(() => {
        // Stop pull down refresh animation
        wx.stopPullDownRefresh();
      })
      .catch(err => {
        console.error('Error refreshing data:', err);
        
        // Stop pull down refresh animation
        wx.stopPullDownRefresh();
        
        // Show error message
        wx.showToast({
          title: '刷新失败，请检查网络',
          icon: 'none',
          duration: 2000
        });
      });
  }
}); 