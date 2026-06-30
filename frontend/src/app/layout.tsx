import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Options Research",
  description: "Personal options trading research platform — NSE/BSE",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          <div className="flex min-h-screen">
            <Nav />
            <main className="flex-1 overflow-auto p-6">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
