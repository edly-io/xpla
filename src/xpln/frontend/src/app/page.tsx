"use client";

import { useEffect, useState, useCallback } from "react";
import { getCourses, createCourse, reorderCourses, type CourseItem } from "@/lib/api";
import { CourseList } from "@/components/course-list";
import { AddForm } from "@/components/add-form";

export default function HomePage() {
  const [courses, setCourses] = useState<CourseItem[]>([]);

  const refresh = useCallback(async () => { setCourses(await getCourses()); }, []);
  useEffect(() => { refresh(); }, [refresh]);

  async function handleAdd(title: string) {
    await createCourse(title);
    await refresh();
    window.dispatchEvent(new Event("sidebar-refresh"));
  }

  async function handleReorder(ids: string[]) {
    setCourses((prev) => ids.map((id) => prev.find((c) => c.id === id)!));
    await reorderCourses(ids);
    window.dispatchEvent(new Event("sidebar-refresh"));
  }

  return (
    <section>
      <h1 className="text-2xl font-bold mb-4">Courses</h1>
      <CourseList courses={courses} onReorder={handleReorder} />
      <AddForm onAdd={handleAdd} placeholder="New course title…" />
    </section>
  );
}
