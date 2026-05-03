"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { AuthPage } from "@/components/views/auth-page";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { OfflineBanner } from "@/components/offline-banner";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <OfflineBanner />
        <main className="p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
