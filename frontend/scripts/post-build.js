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

// 创建_headers文件，设置正确的MIME类型
const headersContent = `/*
  X-Content-Type-Options: nosniff

/_next/static/chunks/*.js
  Content-Type: application/javascript

/_next/static/css/*.css
  Content-Type: text/css

/_next/static/*
  Cache-Control: public, max-age=31536000, immutable
`;

fs.writeFileSync(path.join(outDir, '_headers'), headersContent);
console.log('✅ Created _headers file with proper MIME types');

console.log('🎉 Post-build script completed successfully!'); 