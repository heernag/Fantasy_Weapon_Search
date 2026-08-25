import type { NextConfig } from "next";

const backendBaseUrl = process.env.BACKEND_API_BASE_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/backend/images/:path*", destination: `${backendBaseUrl}/images/:path*` },
      { source: "/api/backend/filters", destination: `${backendBaseUrl}/filters` },
      { source: "/api/backend/search/text", destination: `${backendBaseUrl}/search/text` },
      { source: "/api/backend/search/image", destination: `${backendBaseUrl}/search/image` },
      { source: "/api/backend/search/multimodal", destination: `${backendBaseUrl}/search/multimodal` }
    ];
  }
};

export default nextConfig;
