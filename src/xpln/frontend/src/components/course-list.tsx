"use client";

import Link from "next/link";
import { DndContext, closestCenter, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import type { CourseItem } from "@/lib/api";

function SortableCourse({ course }: { course: CourseItem }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: course.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card className="mb-2">
        <CardContent className="p-3">
          <Link href={`/courses/${course.id}`} className="hover:underline">{course.title}</Link>
        </CardContent>
      </Card>
    </div>
  );
}

type CourseListProps = { courses: CourseItem[]; onReorder: (ids: string[]) => void };

export function CourseList({ courses, onReorder }: CourseListProps) {
  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = courses.findIndex((c) => c.id === active.id);
    const newIndex = courses.findIndex((c) => c.id === over.id);
    const reordered = arrayMove(courses, oldIndex, newIndex);
    onReorder(reordered.map((c) => c.id));
  }

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={courses.map((c) => c.id)} strategy={verticalListSortingStrategy}>
        {courses.map((course) => <SortableCourse key={course.id} course={course} />)}
      </SortableContext>
    </DndContext>
  );
}
