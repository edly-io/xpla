export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { credentials: "include", ...init });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function json(body: unknown): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function jsonMethod(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

// Auth
export type Me = { id: string; email: string };
export const getMe = () => request<Me>("/api/me");
export const signup = (email: string, password: string) => request<Me>("/api/auth/signup", json({ email, password }));
export const login = (email: string, password: string) => request<Me>("/api/auth/login", json({ email, password }));
export const logout = () => request<void>("/api/auth/logout", { method: "POST" });

// API token
export type ApiTokenResponse = { token: string };
export const getApiToken = () => request<ApiTokenResponse>("/api/settings/api-token");
export const regenerateApiToken = () => request<ApiTokenResponse>("/api/settings/api-token", { method: "POST" });

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

// Course dashboard
export type CourseDashboard = { id: string; title: string; activities: Activity[]; activity_types: string[] };
export const getCourseDashboard = (courseId: string) => request<CourseDashboard>(`/api/courses/${courseId}/dashboard`);
export const createCourseActivity = (courseId: string, activity_type: string) => request<Activity>(`/api/courses/${courseId}/dashboard/activities`, json({ activity_type }));
export const getCourseActivity = (id: string, permission: string) => request<Activity>(`/api/course-activities/${id}/${permission}`);
export const deleteCourseActivity = (id: string) => request<void>(`/api/course-activities/${id}`, { method: "DELETE" });
export const moveCourseActivity = (id: string, direction: string, course_id: string) => request<{ activities: Activity[] }>(`/api/course-activities/${id}/move`, json({ direction, course_id }));

// Course activity type management
export const getCourseActivityTypes = () => request<string[]>("/api/course-activity-types");
export const deleteCourseActivityType = (name: string) => request<void>(`/api/course-activity-types/${name}`, { method: "DELETE" });
export const uploadCourseActivityType = (name: string, file: File) => {
  const fd = new FormData();
  fd.append("name", name);
  fd.append("file", file);
  return request<void>("/api/course-activity-types", { method: "POST", body: fd });
};
