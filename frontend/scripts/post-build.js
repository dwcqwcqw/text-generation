const fs = require('fs');
const path = require('path');

console.log('🔧 Running post-build script...');

const outDir = path.join(__dirname, '..', 'out');

// Fix _redirects file
const redirectsPath = path.join(outDir, '_redirects');
const redirectsContent = `# Static assets should be served directly
/_next/static/*  /_next/static/:splat  200
/static/*        /static/:splat        200

# SPA Fallback for Next.js static export - only for HTML routes
/*    /index.html   200
`;

fs.writeFileSync(redirectsPath, redirectsContent, 'utf8');
console.log('✅ Fixed _redirects file');

// Create _headers file
const headersPath = path.join(outDir, '_headers');
const headersContent = `/_next/static/css/*
  Content-Type: text/css

/_next/static/chunks/*.js
  Content-Type: application/javascript

/*
  X-Content-Type-Options: nosniff
`;

fs.writeFileSync(headersPath, headersContent, 'utf8');
console.log('✅ Created _headers file');

console.log('🎉 Post-build script completed!'); 