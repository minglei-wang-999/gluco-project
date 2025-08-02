Component({
  properties: {
    title: {
      type: String,
      value: 'GL Tracker'
    },
    showBack: {
      type: Boolean,
      value: false
    },
    showDate: {
      type: Boolean,
      value: false
    },
    currentDate: {
      type: String,
      value: ''
    }
  },
  
  data: {
    
  },
  
  methods: {
    onBack: function() {
      this.triggerEvent('back');
    },
    
    onPrev: function() {
      this.triggerEvent('prev');
    },
    
    onNext: function() {
      this.triggerEvent('next');
    }
  }
}); 