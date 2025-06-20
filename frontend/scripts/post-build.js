const fs = require('fs');
const path = require('path');

console.log('🔧 Running post-build script...');

const outDir = path.join(__dirname, '..', 'out');

// Remove any existing Cloudflare configuration files to let it auto-detect
const filesToRemove = ['_routes.json', '_headers'];
filesToRemove.forEach(filename => {
  const filePath = path.join(outDir, filename);
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
    console.log(`✅ Removed ${filename} to let Cloudflare auto-detect`);
  }
});

// 复制public中的_redirects文件到out目录
const publicRedirectsPath = path.join(__dirname, '..', 'public', '_redirects');
const outRedirectsPath = path.join(outDir, '_redirects');
if (fs.existsSync(publicRedirectsPath)) {
  fs.copyFileSync(publicRedirectsPath, outRedirectsPath);
  console.log('✅ Copied _redirects file to output directory');
}

// 创建_headers文件，设置正确的MIME类型 - 使用Cloudflare Pages的正确格式
const headersContent = `/_next/static/css/*.css
  Content-Type: text/css

/_next/static/chunks/*.js
  Content-Type: application/javascript

/_next/static/*.js
  Content-Type: application/javascript

/*.js
  Content-Type: application/javascript

/*.css
  Content-Type: text/css
`;

fs.writeFileSync(path.join(outDir, '_headers'), headersContent);
console.log('✅ Created _headers file with proper MIME types');

// 创建_routes.json文件，确保正确的路由处理
const routesContent = `{
  "version": 1,
  "include": ["/", "/test/*", "/debug/*", "/api/*"],
  "exclude": ["/_next/*", "/*.css", "/*.js", "/favicon.ico", "/fix-mime.js"]
}`;

fs.writeFileSync(path.join(outDir, '_routes.json'), routesContent);
console.log('✅ Created _routes.json file for proper routing');

console.log('🎉 Post-build script completed successfully!'); 