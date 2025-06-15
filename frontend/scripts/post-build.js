const fs = require('fs');
const path = require('path');

console.log('🔧 Running post-build script...');

const outDir = path.join(__dirname, '..', 'out');

// Fix _redirects file for Cloudflare Pages
const redirectsPath = path.join(outDir, '_redirects');
const redirectsContent = `# Cloudflare Pages - Next.js static export
# Let static assets be served directly, no redirects for them

# Only handle 404 for non-existent HTML pages
/404.html /404 200
`;

fs.writeFileSync(redirectsPath, redirectsContent, 'utf8');
console.log('✅ Fixed _redirects file for Cloudflare Pages');

// Remove _headers file since Cloudflare should auto-detect MIME types
const headersPath = path.join(outDir, '_headers');
if (fs.existsSync(headersPath)) {
  fs.unlinkSync(headersPath);
  console.log('✅ Removed _headers file - letting Cloudflare auto-detect MIME types');
}

console.log('🎉 Post-build script completed successfully!'); 