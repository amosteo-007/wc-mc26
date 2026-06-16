/** @type {import('next').NextConfig} */
const isProd = process.env.NEXT_PUBLIC_API_URL !== undefined;

const nextConfig = {
  // Static export for Render (and any CDN/static host). The API calls go
  // directly to NEXT_PUBLIC_API_URL in production; the rewrite below only
  // fires in local dev where that var is unset.
  ...(isProd ? { output: "export" } : {}),

  ...(!isProd
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: "http://localhost:8000/:path*",
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
