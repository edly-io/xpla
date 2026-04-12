"use client";

import { usePathname } from "next/navigation";
import { HomePage } from "@/components/views/home-page";
import { ActivitiesPage } from "@/components/views/activities-page";
import { CourseDetailPage } from "@/components/views/course-detail-page";
import { CourseDashboardPage } from "@/components/views/course-dashboard-page";
import { PageDetailPage } from "@/components/views/page-detail-page";
import { SettingsPage } from "@/components/views/settings-page";

export function ClientRouter() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) {
    return <HomePage />;
  }

  if (segments[0] === "activities" && segments.length === 1) {
    return <ActivitiesPage />;
  }

  if (segments[0] === "settings" && segments.length === 1) {
    return <SettingsPage />;
  }

  if (segments[0] === "courses" && segments.length === 3 && segments[2] === "dashboard") {
    return <CourseDashboardPage courseId={segments[1]} />;
  }

  if (segments[0] === "courses" && segments.length === 2) {
    return <CourseDetailPage courseId={segments[1]} />;
  }

  if (segments[0] === "pages" && segments.length === 2) {
    return <PageDetailPage pageId={segments[1]} />;
  }

  return (
    <section>
      <h1 className="text-2xl font-bold mb-4">Not Found</h1>
      <p className="text-muted-foreground">Page not found.</p>
    </section>
  );
}
