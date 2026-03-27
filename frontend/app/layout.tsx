import type { Metadata } from "next";
import { App as AntdApp, ConfigProvider } from "antd";
import { Noto_Sans_SC, Space_Grotesk } from "next/font/google";

import "./globals.css";

const bodyFont = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-body"
});

const displayFont = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-display"
});

export const metadata: Metadata = {
  title: "简历初筛工作台",
  description: "用于招聘团队快速冻结岗位画像、批量筛选简历并生成结构化报告的内部工作台。"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className={`${bodyFont.variable} ${displayFont.variable}`}>
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: "#147d64",
              colorBgBase: "#f5f8f4",
              colorTextBase: "#1d2b26",
              fontFamily: "var(--font-body)"
            }
          }}
        >
          <AntdApp>{children}</AntdApp>
        </ConfigProvider>
      </body>
    </html>
  );
}
