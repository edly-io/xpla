"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { getPage, getActivity, createActivity, updatePage, deletePage, deleteActivity, moveActivity, type PageDetail, type Activity } from "@/lib/api";
import { ActivityList } from "@/components/activity-list";
import { AddForm } from "@/components/add-form";
import { ItemActions } from "@/components/item-actions";

export default function PageDetailPage() {
  const { pageId } = useParams<{ pageId: string }>();
  const router = useRouter();
  const [page, setPage] = useState<PageDetail | null>(null);

  const refresh = useCallback(async () => { setPage(await getPage(pageId)); }, [pageId]);
  useEffect(() => { refresh(); }, [refresh]);

  if (!page) return null;

  async function handleAddActivity(activityType: string) {
    await createActivity(pageId, activityType);
    await refresh();
  }

  async function handleRename(title: string) {
    await updatePage(pageId, title);
    await refresh();
    window.dispatchEvent(new Event("sidebar-refresh"));
  }

  async function handleDelete() {
    const courseId = page!.course_id;
    await deletePage(pageId);
    window.dispatchEvent(new Event("sidebar-refresh"));
    router.push(`/courses/${courseId}`);
  }

  async function handleMove(activityId: string, direction: string) {
    const result = await moveActivity(activityId, direction, pageId);
    setPage((prev) => prev ? { ...prev, activities: result.activities } : prev);
  }

  async function handleDeleteActivity(activityId: string) {
    await deleteActivity(activityId);
    await refresh();
  }

  async function handleTogglePermission(activityId: string, current: string) {
    const newPerm = current === "play" ? "edit" : "play";
    const fresh = await getActivity(activityId, newPerm);
    setPage((prev) => {
      if (!prev) return prev;
      return { ...prev, activities: prev.activities.map((a) =>
        a.id === activityId ? fresh : a
      ) };
    });
  }

  return (
    <section>
      <ItemActions
        title={page.title}
        onRename={handleRename}
        onDelete={handleDelete}
        renderTitle={(title) => <h1 className="text-2xl font-bold">{title}</h1>}
      />
      <div className="mt-4">
        <ActivityList
          activities={page.activities}
          onMove={handleMove}
          onDelete={handleDeleteActivity}
          onTogglePermission={handleTogglePermission}
        />
        <AddForm onAdd={handleAddActivity} options={page.activity_types} />
      </div>
    </section>
  );
}
