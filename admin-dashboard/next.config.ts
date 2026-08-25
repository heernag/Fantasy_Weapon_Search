import type { NextConfig } from "next";
const backendBaseUrl = process.env.BACKEND_API_BASE_URL ?? "http://127.0.0.1:8000";
const nextConfig: NextConfig = { async rewrites() { return [{ source: "/api/backend/evaluation/:path*", destination: `${backendBaseUrl}/evaluation/:path*` }]; } };
export default nextConfig;
