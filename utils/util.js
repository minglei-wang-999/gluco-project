// Utility functions for the app

// Format time as HH:MM
const formatTime = date => {
  const hour = date.getHours();
  const minute = date.getMinutes();

  return [hour, minute].map(formatNumber).join(':');
};

const getMealType = (date) => {
  const hour = date.getHours();
  if (hour >= 5 && hour < 10) {
    return '早餐';
  } else if (hour >= 10 && hour < 15) {
    return '午餐';
  } else if (hour >= 17 && hour < 22) {
    return '晚餐';
  }
  return '零食';
}

// Format time as HH:MM AM/PM
const formatTimeAMPM = date => {
  let hours = date.getHours();
  const minutes = date.getMinutes();
  const ampm = hours >= 12 ? 'PM' : 'AM';
  
  hours = hours % 12;
  hours = hours ? hours : 12; // Handle midnight (0 hours)
  
  return `${formatNumber(hours)}:${formatNumber(minutes)} ${ampm}`;
};

// Format date as YYYY-MM-DD
const formatDate = date => {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();

  return [year, month, day].map(formatNumber).join('-');
};

// Format a single-digit number to two digits
const formatNumber = n => {
  n = n.toString();
  return n[1] ? n : `0${n}`;
};

// Format date as Month DD, YYYY
const formatDateFull = date => {
  const months = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
  const year = date.getFullYear();
  const month = months[date.getMonth()];
  const day = date.getDate();

  return `${year}年${month}月${day}日`;
};

// Get day of week abbreviation (Mon, Tue, etc.)
const getDayOfWeek = date => {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  return days[date.getDay()];
};

// Calculate GL color based on value and goal
const getGLColor = (value, goal) => {
  const ratio = value / (goal || 20);
  if (ratio < 0.7) return '#10B981'; // green-500
  if (ratio < 0.9) return '#F59E0B'; // yellow-500
  return '#EF4444'; // red-500
};

// Get stability score color
const getStabilityColor = (score) => {
  if (score >= 75) return '#10B981'; // green-500
  if (score >= 60) return '#F59E0B'; // yellow-500
  return '#EF4444'; // red-500
};

// Convert ISO date string to local Date object
const isoToDate = (isoString) => {
  return new Date(isoString);
};

/**
 * Convert snake_case to camelCase
 * @param {Object} obj - Object to convert
 * @return {Object} - Converted object
 */
function snakeToCamel(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => snakeToCamel(item));
  }
  
  return Object.keys(obj).reduce((acc, key) => {
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
    
    // Recursively transform nested objects and arrays
    acc[camelKey] = snakeToCamel(obj[key]);
    
    return acc;
  }, {});
}

// Convert local date to UTC date string with time boundary
const getUTCDateString = (date, isEndOfDay = false) => {
  // Create a new date at midnight UTC for the given local date
  const utcDate = new Date(Date.UTC(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
    isEndOfDay ? 23 : 0,
    isEndOfDay ? 59 : 0,
    isEndOfDay ? 59 : 0,
    isEndOfDay ? 999 : 0
  ));
  
  return utcDate.toISOString();
};

module.exports = {
  formatTime,
  formatTimeAMPM,
  formatDate,
  formatDateFull,
  formatNumber,
  getDayOfWeek,
  getGLColor,
  getStabilityColor,
  isoToDate,
  snakeToCamel,
  getMealType,
  getUTCDateString
}; 