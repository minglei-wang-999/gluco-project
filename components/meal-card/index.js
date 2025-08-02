Component({
  properties: {
    meal: {
      type: Object,
      value: {}
    }
  },
  
  data: {
    
  },
  
  methods: {
    onTapMeal: function() {
      this.triggerEvent('tapmeal', { meal: this.properties.meal });
    }
  }
}); 