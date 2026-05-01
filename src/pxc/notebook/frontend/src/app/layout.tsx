import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ActivityRegister } from "@/components/activity-register";
import { AuthProvider } from "@/lib/auth-context";
import { RequireAuth } from "@/components/require-auth";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = { title: "PXC Notebook" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="antialiased">
        <ActivityRegister />
        <TooltipProvider>
          <AuthProvider>
            <RequireAuth>{children}</RequireAuth>
          </AuthProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
