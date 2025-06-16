/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  distDir: 'out',
  images: {
    unoptimized: true
  },
  assetPrefix: '',
  basePath: '',
  generateBuildId: () => 'build-' + Date.now(),
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://api-text-generation.runpod.app',
    NEXT_PUBLIC_R2_BUCKET: process.env.NEXT_PUBLIC_R2_BUCKET || 'text-generation'
  },
  experimental: {
    esmExternals: 'loose'
  },
  // 优化静态资源加载
  poweredByHeader: false,
  reactStrictMode: true,
  swcMinify: true,
  compress: true,
  productionBrowserSourceMaps: false,
  // 确保JS文件被正确处理
  webpack: (config) => {
    config.module.rules.push({
      test: /\.js$/,
      type: 'javascript/auto',
      resolve: {
        fullySpecified: false
      }
    });
    return config;
  }
}

module.exports = nextConfig 