const BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

function json(body: unknown): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function jsonMethod(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

// Courses
export type CourseItem = { id: string; title: string; position: number };
export type CourseDetail = CourseItem & { pages: PageItem[] };

export const getCourses = () => request<CourseItem[]>("/api/courses");
export const createCourse = (title: string) => request<CourseItem>("/api/courses", json({ title }));
export const getCourse = (id: string) => request<CourseDetail>(`/api/courses/${id}`);
export const updateCourse = (id: string, title: string) => request<CourseItem>(`/api/courses/${id}`, jsonMethod("PATCH", { title }));
export const deleteCourse = (id: string) => request<void>(`/api/courses/${id}`, { method: "DELETE" });
export const reorderCourses = (course_ids: string[]) => request<void>("/api/courses/reorder", json({ course_ids }));

// Pages
export type PageItem = { id: string; title: string; position: number };
export type Activity = { id: string; page_id: string; activity_type: string; position: number; client_path: string; state: unknown; permission: string; context: { user_id: string; course_id: string; activity_id: string } };
export type PageDetail = { id: string; title: string; course_id: string; activities: Activity[]; activity_types: string[] };

export const createPage = (courseId: string, title: string) => request<PageItem>(`/api/courses/${courseId}/pages`, json({ title }));
export const getPage = (id: string) => request<PageDetail>(`/api/pages/${id}`);
export const updatePage = (id: string, title: string) => request<PageItem>(`/api/pages/${id}`, jsonMethod("PATCH", { title }));
export const deletePage = (id: string) => request<void>(`/api/pages/${id}`, { method: "DELETE" });
export const reorderPages = (page_ids: string[]) => request<void>("/api/pages/reorder", json({ page_ids }));

// Activities
export const createActivity = (pageId: string, activity_type: string) => request<Activity>(`/api/pages/${pageId}/activities`, json({ activity_type }));
export const getActivity = (id: string, permission: string) => request<Activity>(`/api/activities/${id}/${permission}`);
export const deleteActivity = (id: string) => request<void>(`/api/activities/${id}`, { method: "DELETE" });
export const moveActivity = (id: string, direction: string, page_id: string) => request<{ activities: Activity[] }>(`/api/activities/${id}/move`, json({ direction, page_id }));
export const getActivityTypes = () => request<string[]>("/api/activity-types");

// Activity type management
export const deleteActivityType = (name: string) => request<void>(`/api/activity-types/${name}`, { method: "DELETE" });
export const uploadActivityType = (name: string, file: File) => {
  const fd = new FormData();
  fd.append("name", name);
  fd.append("file", file);
  return request<void>("/api/activity-types", { method: "POST", body: fd });
};
