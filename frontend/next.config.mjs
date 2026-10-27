/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Keep the proxy alive until the browser's bounded API timeout can explain
  // slow first-time market requests instead of returning an opaque proxy 500.
  experimental: { proxyTimeout: 65000 },
  async rewrites() {
    const backend = (
      process.env.BACKEND_URL || "http://127.0.0.1:8000"
    ).replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
export default nextConfig;
