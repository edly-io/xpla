"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { XplActivity } from "@/components/xpl-activity";
import type { Activity } from "@/lib/api";

type ActivityListProps = {
  activities: Activity[];
  onMove: (id: string, direction: string) => void;
  onDelete: (id: string) => void;
  onTogglePermission: (id: string, current: string) => void;
};

export function ActivityList({ activities, onMove, onDelete, onTogglePermission }: ActivityListProps) {
  const [shareActivity, setShareActivity] = useState<{ id: string; permission: string } | null>(null);

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
                  <DropdownMenuItem onClick={() => setShareActivity({ id: a.id, permission: a.permission })}>Share with AI agent</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onDelete(a.id)} className="text-destructive">Delete</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <XplActivity context={a.context} clientPath={a.client_path} state={a.state} permission={a.permission} />
          </CardContent>
        </Card>
      ))}

      <AlertDialog open={shareActivity !== null} onOpenChange={(open) => { if (!open) setShareActivity(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Share with AI agent</AlertDialogTitle>
            <AlertDialogDescription>Share the following URL with your AI agent:</AlertDialogDescription>
          </AlertDialogHeader>
          {shareActivity && (
            <>
              {(() => {
                const llmsUrl = `${process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "")}/api/activities/${shareActivity.id}/${shareActivity.permission}/llms.txt`;
                return (
                  <>
                    <Input
                      readOnly
                      value={llmsUrl}
                      onFocus={(e) => e.target.select()}
                    />
                    <p className="text-sm text-muted-foreground">
                      For instance: &quot;Fetch the content of this page {llmsUrl} and use the information to help me work with this activity&quot;
                    </p>
                  </>
                );
              })()}
            </>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel>Close</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
