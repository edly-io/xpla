"use client";

import Link from "next/link";
import { DndContext, closestCenter, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import type { PageItem } from "@/lib/api";

function SortablePage({ page }: { page: PageItem }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: page.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card className="mb-2">
        <CardContent className="p-3">
          <Link href={`/pages/${page.id}`} className="hover:underline">{page.title}</Link>
        </CardContent>
      </Card>
    </div>
  );
}

type PageListProps = { pages: PageItem[]; onReorder: (ids: string[]) => void };

export function PageList({ pages, onReorder }: PageListProps) {
  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = pages.findIndex((p) => p.id === active.id);
    const newIndex = pages.findIndex((p) => p.id === over.id);
    const reordered = arrayMove(pages, oldIndex, newIndex);
    onReorder(reordered.map((p) => p.id));
  }

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={pages.map((p) => p.id)} strategy={verticalListSortingStrategy}>
        {pages.map((page) => <SortablePage key={page.id} page={page} />)}
      </SortableContext>
    </DndContext>
  );
}
