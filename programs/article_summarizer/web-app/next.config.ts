import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  eslint: {
    // Allow production builds to complete even with ESLint warnings
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Allow production builds to complete even with type errors
    ignoreBuildErrors: true,
  },
  webpack: (config) => {
    // Add webpack alias as fallback for @ path resolution
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, './src'),
    };
    return config;
  },
};

export default nextConfig;
