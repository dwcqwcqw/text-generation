const fs = require('fs');
const path = require('path');

console.log('🔧 Running post-build script...');

const outDir = path.join(__dirname, '..', 'out');

// Create _routes.json file for Cloudflare Pages
const routesPath = path.join(outDir, '_routes.json');
const routesConfig = {
  version: 1,
  description: "Next.js static export routing for Cloudflare Pages",
  include: ["/*"],
  exclude: [
    "/_next/static/*",
    "/_next/static/css/*",
    "/_next/static/chunks/*",
    "/_next/static/media/*",
    "/favicon.ico"
  ]
};

fs.writeFileSync(routesPath, JSON.stringify(routesConfig, null, 2), 'utf8');
console.log('✅ Created _routes.json file for static asset routing');

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