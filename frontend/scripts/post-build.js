const fs = require('fs');
const path = require('path');

console.log('🔧 Running post-build script...');

const outDir = path.join(__dirname, '..', 'out');

// Remove any existing Cloudflare configuration files to let it auto-detect
const filesToRemove = ['_routes.json', '_redirects', '_headers'];
filesToRemove.forEach(filename => {
  const filePath = path.join(outDir, filename);
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
    console.log(`✅ Removed ${filename} to let Cloudflare auto-detect`);
  }
});

console.log('🎉 Post-build script completed successfully!'); 