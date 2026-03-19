"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getCourse, createPage, updateCourse, deleteCourse, reorderPages, type CourseDetail } from "@/lib/api";
import { PageList } from "@/components/page-list";
import { AddForm } from "@/components/add-form";
import { ItemActions } from "@/components/item-actions";

export function CourseDetailPage({ courseId }: { courseId: string }) {
  const router = useRouter();
  const [course, setCourse] = useState<CourseDetail | null>(null);

  const refresh = useCallback(async () => { setCourse(await getCourse(courseId)); }, [courseId]);
  useEffect(() => { refresh(); }, [refresh]);

  if (!course) return null;

  async function handleAddPage(title: string) {
    await createPage(courseId, title);
    await refresh();
    window.dispatchEvent(new Event("sidebar-refresh"));
  }

  async function handleRename(title: string) {
    await updateCourse(courseId, title);
    await refresh();
    window.dispatchEvent(new Event("sidebar-refresh"));
  }

  async function handleDelete() {
    await deleteCourse(courseId);
    window.dispatchEvent(new Event("sidebar-refresh"));
    router.push("/");
  }

  async function handleReorder(ids: string[]) {
    setCourse((prev) => prev ? { ...prev, pages: ids.map((id) => prev.pages.find((p) => p.id === id)!) } : prev);
    await reorderPages(ids);
    window.dispatchEvent(new Event("sidebar-refresh"));
  }

  return (
    <section>
      <ItemActions
        title={course.title}
        onRename={handleRename}
        onDelete={handleDelete}
        renderTitle={(title) => <h1 className="text-2xl font-bold">{title}</h1>}
      />
      <div className="mt-4">
        <PageList pages={course.pages} onReorder={handleReorder} />
        <AddForm onAdd={handleAddPage} placeholder="New page title…" />
      </div>
    </section>
  );
}
