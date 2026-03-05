import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://localhost:9753/api/:path*" },
      { source: "/a/:path*", destination: "http://localhost:9753/a/:path*" },
      { source: "/static/:path*", destination: "http://localhost:9753/static/:path*" },
    ];
  },
};

export default nextConfig;
