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

// 创建_headers文件，设置正确的MIME类型 - 使用最简单的格式
const headersContent = `/*
  Content-Type: text/html; charset=UTF-8
  X-Content-Type-Options: nosniff
  Access-Control-Allow-Origin: *

*.js
  Content-Type: application/javascript

*.css
  Content-Type: text/css

*.json
  Content-Type: application/json
`;

fs.writeFileSync(path.join(outDir, '_headers'), headersContent);
console.log('✅ Created _headers file with proper MIME types');

// 创建_routes.json文件，确保正确的路由处理
const routesContent = `{
  "version": 1,
  "include": ["/*"],
  "exclude": []
}`;

fs.writeFileSync(path.join(outDir, '_routes.json'), routesContent);
console.log('✅ Created _routes.json file for proper routing');

console.log('🎉 Post-build script completed successfully!'); 