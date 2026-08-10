/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // In development: proxy /api/* to the local FastAPI backend (port 8000)
  // In production on Vercel: /api/* is handled natively by the Python serverless function
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: "http://127.0.0.1:8000/api/:path*",
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
