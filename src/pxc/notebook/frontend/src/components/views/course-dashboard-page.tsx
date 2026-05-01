"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { getCourseDashboard, getCourseActivity, createCourseActivity, deleteCourseActivity, moveCourseActivity, uploadCourseActivityType, deleteCourseActivityType, type CourseDashboard, type Activity } from "@/lib/api";
import { ActivityList } from "@/components/activity-list";
import { AddForm } from "@/components/add-form";

export function CourseDashboardPage({ courseId }: { courseId: string }) {
  const [dashboard, setDashboard] = useState<CourseDashboard | null>(null);
  const [uploadName, setUploadName] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => { setDashboard(await getCourseDashboard(courseId)); }, [courseId]);
  useEffect(() => { refresh(); }, [refresh]);

  if (!dashboard) return null;

  async function handleAddActivity(activityType: string) {
    await createCourseActivity(courseId, activityType);
    await refresh();
  }

  async function handleMove(activityId: string, direction: string) {
    const result = await moveCourseActivity(activityId, direction, courseId);
    setDashboard((prev) => prev ? { ...prev, activities: result.activities } : prev);
  }

  async function handleDeleteActivity(activityId: string) {
    await deleteCourseActivity(activityId);
    await refresh();
  }

  async function handleTogglePermission(activityId: string, current: string) {
    const newPerm = current === "play" ? "edit" : "play";
    const fresh = await getCourseActivity(activityId, newPerm);
    setDashboard((prev) => {
      if (!prev) return prev;
      return { ...prev, activities: prev.activities.map((a: Activity) =>
        a.id === activityId ? fresh : a
      ) };
    });
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    setUploadError(null);
    const file = fileRef.current?.files?.[0];
    if (!file || !uploadName) return;
    try {
      await uploadCourseActivityType(uploadName, file);
      setUploadName("");
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function handleDeleteType(activityType: string) {
    const name = activityType.split("/").slice(1).join("/");
    await deleteCourseActivityType(name);
    await refresh();
  }

  // User-uploaded types (those starting with @)
  const uploadedTypes = dashboard.activity_types.filter((t) => t.startsWith("@"));

  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <Link href={`/courses/${courseId}`} className="text-muted-foreground hover:underline">&larr; Course</Link>
        <h1 className="text-2xl font-bold">Dashboard &mdash; {dashboard.title}</h1>
      </div>
      <div className="mt-4">
        <ActivityList
          activities={dashboard.activities}
          onMove={handleMove}
          onDelete={handleDeleteActivity}
          onTogglePermission={handleTogglePermission}
        />
        <AddForm onAdd={handleAddActivity} options={dashboard.activity_types} />
      </div>

      <hr className="my-8" />

      <h2 className="text-xl font-bold mb-4">Course Activity Types</h2>

      <form onSubmit={handleUpload} className="flex gap-2 items-end mb-6">
        <input
          type="text"
          placeholder="Activity name (e.g. my-dashboard)"
          value={uploadName}
          onChange={(e) => setUploadName(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        />
        <input ref={fileRef} type="file" accept=".zip" className="text-sm" />
        <button
          type="submit"
          className="bg-primary text-primary-foreground px-3 py-1 rounded text-sm"
        >
          Upload
        </button>
      </form>

      {uploadError && <p className="text-red-600 text-sm mb-4">{uploadError}</p>}

      {uploadedTypes.length === 0 ? (
        <p className="text-muted-foreground text-sm">No uploaded course activity types yet.</p>
      ) : (
        <ul className="space-y-2">
          {uploadedTypes.map((a) => (
            <li key={a} className="flex items-center gap-2">
              <span className="text-sm font-mono">{a}</span>
              <button
                onClick={() => handleDeleteType(a)}
                className="text-red-600 text-xs hover:underline"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
