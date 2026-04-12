"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { DndContext, closestCenter, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from "@dnd-kit/sortable";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
} from "@/components/ui/sidebar";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { getCourses, getCourse, reorderPages, type CourseItem, type PageItem } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function SortablePage({ page, isActive }: { page: PageItem; isActive: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: page.id });
  const style: React.CSSProperties = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    transition: transition ?? undefined,
  };

  return (
    <SidebarMenuSubItem ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <SidebarMenuSubButton
        isActive={isActive}
        render={<Link href={`/pages/${page.id}`} />}
      >
        {page.title}
      </SidebarMenuSubButton>
    </SidebarMenuSubItem>
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [activeCourseId, setActiveCourseId] = useState<string | null>(null);
  const [pages, setPages] = useState<PageItem[]>([]);

  const refresh = useCallback(async () => {
    setCourses(await getCourses());
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    const courseMatch = pathname.match(/^\/courses\/([^/]+)/);
    const pageMatch = pathname.match(/^\/pages\/([^/]+)/);
    if (courseMatch) {
      setActiveCourseId(courseMatch[1]);
    } else if (pageMatch) {
      import("@/lib/api").then(({ getPage }) =>
        getPage(pageMatch[1]).then((p) => setActiveCourseId(p.course_id))
      );
    } else {
      setActiveCourseId(null);
    }
  }, [pathname]);

  useEffect(() => {
    if (activeCourseId) {
      getCourse(activeCourseId).then((c) => setPages(c.pages));
    } else {
      setPages([]);
    }
  }, [activeCourseId]);

  useEffect(() => {
    const handler = () => { refresh(); if (activeCourseId) getCourse(activeCourseId).then((c) => setPages(c.pages)); };
    window.addEventListener("sidebar-refresh", handler);
    return () => window.removeEventListener("sidebar-refresh", handler);
  }, [refresh, activeCourseId]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setPages((prev) => {
      const oldIndex = prev.findIndex((p) => p.id === active.id);
      const newIndex = prev.findIndex((p) => p.id === over.id);
      const reordered = arrayMove(prev, oldIndex, newIndex);
      reorderPages(reordered.map((p) => p.id));
      return reordered;
    });
  }

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center justify-between">
          <Link href="/" className="px-2 py-1 text-xl font-bold">xPLN</Link>
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="ghost" size="sm" />}>⋯</DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem render={<Link href="/activities" />}>My Activities</DropdownMenuItem>
              <DropdownMenuItem render={<Link href="/settings" />}>Settings</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarMenu>
          {courses.map((course) => (
            <SidebarMenuItem key={course.id}>
              <SidebarMenuButton
                isActive={activeCourseId === course.id && !pathname.includes("/pages/")}
                render={<Link href={`/courses/${course.id}`} />}
              >
                {course.title}
              </SidebarMenuButton>
              {activeCourseId === course.id && pages.length > 0 && (
                <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                  <SortableContext items={pages.map((p) => p.id)} strategy={verticalListSortingStrategy}>
                    <SidebarMenuSub>
                      {pages.map((page) => (
                        <SortablePage
                          key={page.id}
                          page={page}
                          isActive={pathname === `/pages/${page.id}`}
                        />
                      ))}
                    </SidebarMenuSub>
                  </SortableContext>
                </DndContext>
              )}
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center justify-between gap-2 px-2 py-1 text-xs">
          <span className="truncate text-muted-foreground" title={user?.email}>
            {user?.email}
          </span>
          <Button variant="ghost" size="sm" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
