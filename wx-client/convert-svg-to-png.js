const fs = require("fs");
const path = require("path");
const sharp = require("sharp");
const iconNames = ["icon-home", "icon-log", "icon-reports", "icon-settings"];
const states = ["", "-active"];

async function convertSvgToPng() {
  for (const iconName of iconNames) {
    for (const state of states) {
      const svgFilename = `${iconName}${state}.svg`;
      const pngFilename = `${iconName}${state}.png`;
      const svgPath = path.join(__dirname, "images", svgFilename);
      const pngPath = path.join(__dirname, "images", pngFilename);
      try {
        const svgContent = fs.readFileSync(svgPath, "utf-8");
        const color = state === "-active" ? "#3B82F6" : "#999999";
        const coloredSvg = svgContent.replace(
          /stroke="[^"]*"/g,
          `stroke="${color}"`,
        );
        await sharp(Buffer.from(coloredSvg))
          .resize(32, 32)
          .png()
          .toFile(pngPath);
        console.log(`Converted ${svgFilename} to ${pngFilename}`);
      } catch (error) {
        console.error(`Error converting ${svgFilename}:`, error);
      }
    }
  }
}

convertSvgToPng().catch(console.error);
