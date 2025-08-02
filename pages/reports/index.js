const util = require('../../utils/util.js');
const api = require('../../utils/api.js');

Page({
  data: {
    isLoading: true,
    weeklyData: [],
    mealHistory: [],
    currentWeekOffset: 0, // 0 = current week, -1 = previous week, 1 = next week
    dateRange: {
      start: '',
      end: '',
      label: ''
    },
    showInfo: false, // Add showInfo state for the info popover
    // Add meal detail modal state
    showMealDetail: false,
    selectedMeal: null,
    // Mock data for development
    mockData: {
      weeklyMeals: [
        { 
          day: "周一", 
          meals: [
            { time: "07:30", name: "早餐", gl: 22, items: "燕麦粥, 蓝莓, 杏仁奶" },
            { time: "12:15", name: "午餐", gl: 35, items: "鸡肉沙拉, 全麦面包, 苹果" },
            { time: "15:30", name: "零食", gl: 11, items: "希腊酸奶, 核桃" },
            { time: "19:00", name: "晚餐", gl: 28, items: "三文鱼, 藜麦, 蔬菜" }
          ]
        },
        { 
          day: "周二", 
          meals: [
            { time: "08:00", name: "早餐", gl: 18, items: "鸡蛋, 牛油果, 吐司" },
            { time: "13:00", name: "午餐", gl: 42, items: "意大利面, 沙拉, 蒜蓉面包" },
            { time: "16:00", name: "零食", gl: 8, items: "奶酪, 饼干" },
            { time: "19:30", name: "晚餐", gl: 24, items: "炒菜, 糙米" }
          ]
        },
        { 
          day: "周三", 
          meals: [
            { time: "07:45", name: "早餐", gl: 20, items: "酸奶, 格兰诺拉麦片, 香蕉" },
            { time: "12:30", name: "午餐", gl: 32, items: "三明治, 汤" },
            { time: "15:45", name: "零食", gl: 12, items: "苹果, 花生酱" },
            { time: "18:30", name: "晚餐", gl: 26, items: "鸡肉, 红薯, 西兰花" }
          ]
        },
        { 
          day: "周四", 
          meals: [
            { time: "08:15", name: "早餐", gl: 25, items: "煎饼, 糖浆, 浆果" },
            { time: "12:45", name: "午餐", gl: 48, items: "汉堡, 薯条" },
            { time: "16:30", name: "零食", gl: 14, items: "坚果混合" },
            { time: "19:15", name: "晚餐", gl: 32, items: "意大利面, 肉丸, 沙拉" }
          ]
        },
        { 
          day: "周五", 
          meals: [
            { time: "07:30", name: "早餐", gl: 16, items: "思慕雪, 吐司" },
            { time: "12:00", name: "午餐", gl: 30, items: "米饭碗, 鸡肉" },
            { time: "15:15", name: "零食", gl: 9, items: "水果, 坚果" },
            { time: "18:45", name: "晚餐", gl: 22, items: "鱼, 蔬菜, 米饭" }
          ]
        },
        { 
          day: "周六", 
          meals: [
            { time: "09:00", name: "早餐", gl: 28, items: "华夫饼, 糖浆, 培根" },
            { time: "13:30", name: "午餐", gl: 45, items: "披萨, 沙拉" },
            { time: "16:45", name: "零食", gl: 15, items: "曲奇, 牛奶" },
            { time: "20:00", name: "晚餐", gl: 38, items: "牛排, 土豆, 蔬菜" }
          ]
        },
        { 
          day: "周日", 
          meals: [
            { time: "09:30", name: "早餐", gl: 24, items: "百吉饼, 奶油奶酪, 水果" },
            { time: "13:15", name: "午餐", gl: 28, items: "面包卷, 薯片" },
            { time: "16:00", name: "零食", gl: 10, items: "爆米花" },
            { time: "19:00", name: "晚餐", gl: 32, items: "烤鸡, 土豆, 蔬菜" }
          ]
        }
      ],
      pastMeals: [
        {
          day: "昨天 (2月25日)",
          meals: [
            { time: "8:15 AM", name: "早餐", gl: 22, items: "燕麦粥, 浆果", img: "/images/meals/breakfast.svg" },
            { time: "12:30 PM", name: "午餐", gl: 38, items: "三明治, 薯片, 苹果", img: "/images/meals/lunch.svg" },
            { time: "7:45 PM", name: "晚餐", gl: 25, items: "三文鱼, 糙米, 蔬菜", img: "/images/meals/dinner.svg" }
          ]
        },
        {
          day: "星期一 (2月24日)",
          meals: [
            { time: "7:30 AM", name: "早餐", gl: 18, items: "鸡蛋, 吐司", img: "/images/meals/breakfast.svg" },
            { time: "1:00 PM", name: "午餐", gl: 32, items: "墨西哥卷饼, 碳酸饮料", img: "/images/meals/lunch.svg" },
            { time: "6:15 PM", name: "晚餐", gl: 45, items: "意大利面, 蒜蓉面包, 沙拉", img: "/images/meals/dinner.svg" }
          ]
        }
      ]
    }
  },

  onLoad: function () {
    this.setDateRange(0);
    
    // Check if user is logged in
    const app = getApp();
    if (!app.globalData.isLogin) {
      this.handleLogin();
    } else {
      // Use this for real data in the future
      // this.setupMockData();
      this.fetchReportData();
    }
  },
  
  onShow: function() {
    // In real app, we might refresh data here
    const app = getApp();
    if (app.globalData.needRefresh) {
      this.fetchReportData();
      app.globalData.needRefresh = false;
    }
  },
  
  handleLogin: function() {
    const app = getApp();
    app.login((success) => {
      if (!success) {
        wx.showToast({
          title: '登录失败，请重试',
          icon: 'none'
        });
      }
    });
  },
  
  setDateRange: function(weekOffset = 0) {
    // Set date range for the week with the given offset (Sunday to Saturday)
    const today = new Date();
    
    // Apply the week offset
    today.setDate(today.getDate() + (weekOffset * 7));
    
    const day = today.getDay(); // 0 is Sunday, 6 is Saturday
    
    // Calculate the first day of the week (Sunday)
    const firstDay = new Date(today);
    firstDay.setDate(today.getDate() - day);
    
    // Calculate the last day of the week (Saturday)
    const lastDay = new Date(today);
    lastDay.setDate(today.getDate() + (6 - day));
    
    this.setData({
      currentWeekOffset: weekOffset,
      dateRange: {
        start: util.formatDate(firstDay),
        end: util.formatDate(lastDay),
        label: `${util.formatDate(firstDay)} - ${util.formatDate(lastDay)}`
      }
    });
  },
  
  setupMockData: function() {
    // Process mock data for display
    const weeklyMeals = this.data.mockData.weeklyMeals;
    const pastMeals = this.data.mockData.pastMeals;
    
    // Process weekly meals to ensure proper positioning
    weeklyMeals.forEach(dayData => {
      dayData.meals.forEach(meal => {
        // Add color classes based on GL value
        meal.glColor = util.getGLColor(meal.gl, 40);
        
        // Calculate position for dot representation
        meal.position = this.timeToPosition(meal.time);
        // Height is no longer needed for dots
        meal.height = 0;
      });
    });
    
    // Add color classes to past meals
    pastMeals.forEach(dayData => {
      dayData.meals.forEach(meal => {
        meal.glColor = util.getGLColor(meal.gl, 40);
        
        // Convert AM/PM format to 24-hour format for past meals if needed
        if (meal.time.includes('AM') || meal.time.includes('PM')) {
          const [timePart, ampm] = meal.time.split(' ');
          const [hours, minutes] = timePart.split(':').map(Number);
          
          let hour24 = hours;
          if (ampm === 'PM' && hours < 12) hour24 += 12;
          if (ampm === 'AM' && hours === 12) hour24 = 0;
          
          meal.time = `${hour24.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
          console.log(`Converted time: ${timePart} ${ampm} -> ${meal.time}`);
        }
      });
    });
    
    this.setData({
      weeklyData: weeklyMeals,
      mealHistory: pastMeals,
      isLoading: false
    });
  },
  
  fetchReportData: function() {
    // This will be implemented to fetch real data
    this.setData({ isLoading: true });
    
    // Convert start and end dates to UTC
    const startDate = new Date(this.data.dateRange.start);
    const endDate = new Date(this.data.dateRange.end);
    
    // Get UTC date strings for start and end of day
    const startUTC = util.getUTCDateString(startDate);
    const endUTC = util.getUTCDateString(endDate, true);
    
    console.log('UTC date range:', { startUTC, endUTC });
    
    api.getMealHistory(startUTC, endUTC)
      .then(data => {
        console.log('data', data);
        const meals = data.map(meal => util.snakeToCamel(meal));

        // Process meals into the correct format
        const processedMeals = meals.map(meal => {
          const mealTime = new Date(meal.mealTime+"Z");
          return {
            id: meal.id,
            day: mealTime.getDay(),
            time: util.formatTimeAMPM(mealTime), // Use AM/PM format
            name: util.getMealType(mealTime),
            totalGl: meal.totalGl, // Use totalGl instead of gl
            glCategory: meal.totalGl > 20 ? 'high' : (meal.totalGl > 10 ? 'medium' : 'low'),
            items: meal.ingredients.map(ingredient => ingredient.name).join(', '),
            position: this.timeToPosition(util.formatTime(mealTime)), // Keep 24-hour format for position calculation
            height: 0,
            hasDistributionIssue: false, // Add this field
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

        console.log('processedMeals', processedMeals);

        // Create the weekly data structure that matches the template expectations
        const days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
        const weeklyData = days.map((dayName, index) => {
          // Filter meals for this day
          const dayMeals = processedMeals.filter(meal => meal.day === index);
          
          // Sort meals by time
          dayMeals.sort((a, b) => {
            const timeA = a.time.split(':').map(Number);
            const timeB = b.time.split(':').map(Number);
            
            // Compare hours first, then minutes
            if (timeA[0] !== timeB[0]) return timeA[0] - timeB[0];
            return timeA[1] - timeB[1];
          });
          
          console.log('dayMeals', dayMeals);
          return {
            day: dayName,
            meals: dayMeals
          };
        });

        console.log('weeklyData', weeklyData);
        // Process history data (past meals)
        const historyData = meals.reduce((acc, meal) => {
          const mealTime = new Date(meal.mealTime+"Z");
          const formattedTime = util.formatTimeAMPM(mealTime); // Use AM/PM format
          const day = mealTime.getDay();
          const dayOfWeek = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][day];
          const date = `${dayOfWeek} (${mealTime.getFullYear()}年${mealTime.getMonth() + 1}月${mealTime.getDate()}日)`;
          if (!acc[date]) {
            acc[date] = { day: date, meals: [] };
          }
          acc[date].meals.push({
            id: meal.id,
            time: formattedTime,
            name: util.getMealType(mealTime),
            totalGl: meal.totalGl, // Use totalGl instead of gl
            glCategory: meal.totalGl > 20 ? 'high' : (meal.totalGl > 10 ? 'medium' : 'low'),
            items: meal.ingredients.map(ingredient => ingredient.name).join(', '),
            hasDistributionIssue: false, // Add this field
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
          });
          return acc;
        }, {});

        console.log('historyData', historyData);

        this.setData({
          weeklyData: weeklyData,
          mealHistory: Object.values(historyData),
          isLoading: false
        });
      })
      .catch(err => {
        console.error('Error fetching report data:', err);
        this.setData({ isLoading: false });
        wx.showToast({
          title: '获取数据失败',
          icon: 'none'
        });
      });
  },
  
  onPrevWeek: function() {
    // Calculate new week offset
    const newOffset = this.data.currentWeekOffset - 1;
    
    // Update date range with new offset
    this.setDateRange(newOffset);
    
    // Fetch data for the new date range
    this.fetchReportData();
  },
  
  onNextWeek: function() {
    // Calculate new week offset
    const newOffset = this.data.currentWeekOffset + 1;
    
    // Don't allow navigating to future weeks beyond current week
    if (newOffset > 0) {
      wx.showToast({
        title: '无法查看未来的数据',
        icon: 'none'
      });
      return;
    }
    
    // Update date range with new offset
    this.setDateRange(newOffset);
    
    // Fetch data for the new date range
    this.fetchReportData();
  },
  
  onTapMeal: function(e) {
    const meal = e.detail.meal;
    console.log('Tapped meal:', meal);
    
    // Show meal detail modal
    this.setData({
      selectedMeal: meal,
      showMealDetail: true
    });
  },
  
  closeMealDetail: function() {
    this.setData({
      showMealDetail: false,
      selectedMeal: null
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
  
  toggleInfo: function(e) {
    // We don't need to stop propagation here since we're using catchtap in the WXML
    // which already prevents event bubbling
    this.setData({
      showInfo: !this.data.showInfo
    });
  },
  
  // Handle page tap to close popover
  onPageTap: function() {
    if (this.data.showInfo) {
      this.setData({
        showInfo: false
      });
    }
  },
  
  /**
   * Convert time string (e.g., "08:30") to position percentage for vertical placement
   */
  timeToPosition: function(timeStr) {
    // Assuming the day starts at 6 AM (0%) and ends at 10 PM (100%)
    const [hours, minutes] = timeStr.split(':').map(Number);
    
    // Convert to hours since 6 AM
    const hoursSince6am = hours + (minutes / 60) - 6;
    
    // Calculate percentage within the 18-hour window (6 AM to 12 PM)
    const percentage = (hoursSince6am / 18) * 100;
    
    // Clamp within 0-100% range
    return Math.max(0, Math.min(100, percentage));
  },
  
  /**
   * Return standard height for meal blocks
   * Note: This is no longer used for dots, but kept for backward compatibility
   */
  getMealHeight: function() {
    // For dots, we don't need height as they have fixed dimensions
    return 0;
  },

  // Helper function to organize meals by weekday
  organizeByWeekday: function(meals) {
    // Create an array for each day of the week
    const days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
    const weeklyData = days.map(day => ({ day, meals: [] }));
    
    // Group meals by day of week
    meals.forEach(meal => {
      const mealDate = new Date(meal.originalDate || meal.mealTime+"Z");
      const dayIndex = mealDate.getDay(); // 0 is Sunday, 6 is Saturday
      
      weeklyData[dayIndex].meals.push(meal);
    });
    
    // Sort meals by time within each day
    weeklyData.forEach(day => {
      day.meals.sort((a, b) => {
        const timeA = a.time.split(':').map(Number);
        const timeB = b.time.split(':').map(Number);
        
        // Compare hours first, then minutes
        if (timeA[0] !== timeB[0]) return timeA[0] - timeB[0];
        return timeA[1] - timeB[1];
      });
    });
    
    return weeklyData;
  },

  // Helper function to organize meals for history view
  organizeMealHistory: function(meals) {
    // Group meals by date
    const mealsByDate = {};
    
    meals.forEach(meal => {
      const mealDate = new Date(meal.originalDate || meal.mealTime+"Z");
      const dateKey = util.formatDate(mealDate);
      
      if (!mealsByDate[dateKey]) {
        mealsByDate[dateKey] = {
          day: this.formatHistoryDate(mealDate),
          meals: []
        };
      }
      
      mealsByDate[dateKey].meals.push(meal);
    });
    
    // Convert to array and sort by date (newest first)
    const historyData = Object.values(mealsByDate).sort((a, b) => {
      const dateA = new Date(a.day.split('(')[1].split(')')[0]);
      const dateB = new Date(b.day.split('(')[1].split(')')[0]);
      return dateB - dateA;
    });
    
    // Sort meals within each day by time (newest first)
    historyData.forEach(day => {
      day.meals.sort((a, b) => {
        const timeA = a.time.split(':').map(Number);
        const timeB = b.time.split(':').map(Number);
        
        // Compare hours first, then minutes (descending)
        if (timeA[0] !== timeB[0]) return timeB[0] - timeA[0];
        return timeB[1] - timeA[1];
      });
    });
    
    return historyData;
  },

  // Format date for history display (e.g., "昨天 (2月25日)")
  formatHistoryDate: function(date) {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    
    // Check if date is today or yesterday
    if (date.toDateString() === today.toDateString()) {
      return `今天 (${date.getMonth() + 1}月${date.getDate()}日)`;
    } else if (date.toDateString() === yesterday.toDateString()) {
      return `昨天 (${date.getMonth() + 1}月${date.getDate()}日)`;
    }
    
    // Otherwise use day of week
    const days = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    return `${days[date.getDay()]} (${date.getMonth() + 1}月${date.getDate()}日)`;
  },

  // Add this to onLoad or setupMockData to test positioning
  testTimePositioning: function() {
    // Test various times throughout the day
    const testTimes = [
      "06:00", // 6 AM - should be at 0%
      "10:00", // 10 AM - should be at 25%
      "14:00", // 2 PM - should be at 50%
      "18:00", // 6 PM - should be at 75%
      "22:00"  // 10 PM - should be at 100%
    ];
    
    console.log("=== TIME POSITION TEST CASES ===");
    testTimes.forEach(time => {
      const position = this.timeToPosition(time);
      console.log(`Test time: ${time}, Position: ${position}%`);
    });
    console.log("===============================");
  }
}); 