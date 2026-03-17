"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { XplActivity } from "@/components/xpl-activity";
import type { Activity } from "@/lib/api";

type ActivityListProps = {
  activities: Activity[];
  onMove: (id: string, direction: string) => void;
  onDelete: (id: string) => void;
  onTogglePermission: (id: string, current: string) => void;
};

export function ActivityList({ activities, onMove, onDelete, onTogglePermission }: ActivityListProps) {
  return (
    <div>
      {activities.map((a) => (
        <Card key={`${a.id}-${a.permission}`} className="mb-4">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{a.activity_type}</Badge>
                <Button variant="ghost" size="sm" onClick={() => onMove(a.id, "up")}>&#9650;</Button>
                <Button variant="ghost" size="sm" onClick={() => onMove(a.id, "down")}>&#9660;</Button>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger render={<Button variant="ghost" size="sm" />}>⋯</DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => onTogglePermission(a.id, a.permission)}>
                    {a.permission === "play" ? "Edit" : "Play"}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onDelete(a.id)} className="text-destructive">Delete</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <XplActivity scope={a.scope} clientPath={a.client_path} state={a.state} permission={a.permission} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
