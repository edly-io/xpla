"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { getActivityTypes, deleteActivityType, uploadActivityType } from "@/lib/api";

export function ActivitiesPage() {
  const [activities, setActivities] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const all = await getActivityTypes();
    setActivities(all.filter((t) => t.startsWith("@")));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const file = fileRef.current?.files?.[0];
    if (!file || !name) return;
    try {
      await uploadActivityType(name, file);
      setName("");
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function handleDelete(activityType: string) {
    // activityType is "@user/name", extract name part
    const name = activityType.split("/").slice(1).join("/");
    await deleteActivityType(name);
    await refresh();
  }

  return (
    <section>
      <h1 className="text-2xl font-bold mb-4">My Activities</h1>

      <form onSubmit={handleUpload} className="flex gap-2 items-end mb-6">
        <input
          type="text"
          placeholder="Activity name (e.g. my-quiz)"
          value={name}
          onChange={(e) => setName(e.target.value)}
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

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {activities.length === 0 ? (
        <p className="text-muted-foreground text-sm">No uploaded activities yet.</p>
      ) : (
        <ul className="space-y-2">
          {activities.map((a) => (
            <li key={a} className="flex items-center gap-2">
              <span className="text-sm font-mono">{a}</span>
              <button
                onClick={() => handleDelete(a)}
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
