const fs = require('fs');
const path = require('path');

console.log('🔧 Running post-build script...');

const outDir = path.join(__dirname, '..', 'out');

// Create minimal _redirects file - let Cloudflare handle everything automatically
const redirectsPath = path.join(outDir, '_redirects');
const redirectsContent = `# Cloudflare Pages - Next.js static export
# No redirects - let Cloudflare serve files directly
`;

fs.writeFileSync(redirectsPath, redirectsContent, 'utf8');
console.log('✅ Created minimal _redirects file');

// Ensure no _headers file exists
const headersPath = path.join(outDir, '_headers');
if (fs.existsSync(headersPath)) {
  fs.unlinkSync(headersPath);
  console.log('✅ Removed _headers file');
}

console.log('🎉 Post-build script completed successfully!'); 