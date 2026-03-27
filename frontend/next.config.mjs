/** @type {import('next').NextConfig} */
const basePath = process.env.PAGES_BASE_PATH ?? "";

const nextConfig = {
  typedRoutes: false,
  output: "export",
  basePath,
  assetPrefix: basePath || undefined,
  images: {
    unoptimized: true
  },
  trailingSlash: true
};

export default nextConfig;
