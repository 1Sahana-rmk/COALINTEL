import path from 'path';

const nextConfig = {
  reactStrictMode: true,

  webpack: (config) => {
    config.resolve.alias['@'] = path.resolve(process.cwd());

    return config;
  },

  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';

    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;