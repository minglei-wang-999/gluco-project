const resizeImage = (canvasId, imagePath, componentInstance) => {
    return new Promise((resolve, reject) => {
      const MAX_SIZE = 800;
      
      // Get the image info to determine original dimensions
      wx.getImageInfo({
        src: imagePath,
        success: (imageInfo) => {
          console.log('Image info success:', imageInfo);
          const { width, height } = imageInfo;
          
          // Calculate new dimensions maintaining aspect ratio
          let newWidth = width;
          let newHeight = height;
          
          if (width > MAX_SIZE || height > MAX_SIZE) {
            if (width > height) {
              newWidth = MAX_SIZE;
              newHeight = (height * MAX_SIZE) / width;
            } else {
              newHeight = MAX_SIZE;
              newWidth = (width * MAX_SIZE) / height;
            }
          }
          
          // Create canvas context with explicit component instance
          const ctx = wx.createCanvasContext(canvasId, componentInstance);
          
          // Draw and resize image
          ctx.drawImage(imagePath, 0, 0, width, height, 0, 0, newWidth, newHeight);
          ctx.draw(false, () => {
            console.log('Canvas draw completed');
            // Add timeout to ensure canvas has finished rendering
            setTimeout(() => {
              // Convert canvas to temp file with explicit component instance
              wx.canvasToTempFilePath({
                canvasId: canvasId,
                x: 0,
                y: 0,
                width: newWidth,
                height: newHeight,
                destWidth: newWidth,
                destHeight: newHeight,
                fileType: "jpg",
                quality: 0.8,
                success: (res) => resolve(res.tempFilePath),
                fail: (err) => {
                  console.error('Canvas to temp file failed:', err);
                  reject(err);
                }
              }, componentInstance);
            }, 200); // Short delay to ensure canvas is ready
          });
        },
        fail: (err) => {
          console.error('Image info failed:', err);
          reject(err);
        }
      });
    });
};

module.exports = {
  resizeImage
};