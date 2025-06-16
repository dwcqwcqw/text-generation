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
    esmExternals: true
  },
  // 优化静态资源加载
  poweredByHeader: false,
  reactStrictMode: false,
  swcMinify: true,
  compress: true,
  productionBrowserSourceMaps: false,
  // 确保JS文件被正确处理
  webpack: (config) => {
    // 确保JavaScript文件被正确处理
    config.module.rules.push({
      test: /\.js$/,
      type: 'javascript/auto',
      resolve: {
        fullySpecified: false
      }
    });
    
    // 确保静态资源路径正确
    config.output.publicPath = '/';
    
    return config;
  }
}

module.exports = nextConfig 