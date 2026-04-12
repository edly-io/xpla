"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { XplActivity } from "@/components/xpl-activity";
import { getApiToken, type Activity } from "@/lib/api";

type ActivityListProps = {
  activities: Activity[];
  onMove: (id: string, direction: string) => void;
  onDelete: (id: string) => void;
  onTogglePermission: (id: string, current: string) => void;
};

export function ActivityList({ activities, onMove, onDelete, onTogglePermission }: ActivityListProps) {
  const [shareActivity, setShareActivity] = useState<{ id: string; permission: string } | null>(null);
  const [ltiActivity, setLtiActivity] = useState<{ id: string } | null>(null);
  const [apiToken, setApiToken] = useState<string | null>(null);

  useEffect(() => {
    getApiToken().then((r) => setApiToken(r.token));
  }, []);

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
                  <DropdownMenuItem onClick={() => setLtiActivity({ id: a.id })}>Embed via LTI</DropdownMenuItem>
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
                const origin = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "");
                const llmsUrl = `${origin}/api/activities/${shareActivity.id}/${shareActivity.permission}/llms.txt`;
                const prompt = apiToken
                  ? `Fetch the content of this page ${llmsUrl} using the HTTP header "Authorization: Bearer ${apiToken}" and use the information to help me work with this activity`
                  : `Fetch the content of this page ${llmsUrl} and use the information to help me work with this activity`;
                return (
                  <>
                    <Input
                      readOnly
                      value={prompt}
                      onFocus={(e) => e.target.select()}
                    />
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

      <AlertDialog open={ltiActivity !== null} onOpenChange={(open) => { if (!open) setLtiActivity(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Embed this activity via LTI</AlertDialogTitle>
            <AlertDialogDescription>
              Register this tool in your LTI 1.3 platform (e.g., Open edX) with the URLs below, then add a resource link with the custom parameter shown.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {ltiActivity && (() => {
            const origin = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? window.location.origin : "");
            const loginUrl = `${origin}/lti/auth/login`;
            const redirectUri = `${origin}/lti/auth/callback`;
            const jwksUrl = `${origin}/lti/.well-known/jwks.json`;
            const customParam = `activity_id=${ltiActivity.id}`;
            return (
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium">OIDC Login URL</label>
                  <Input readOnly value={loginUrl} onFocus={(e) => e.target.select()} />
                </div>
                <div>
                  <label className="text-sm font-medium">Redirect URI</label>
                  <Input readOnly value={redirectUri} onFocus={(e) => e.target.select()} />
                </div>
                <div>
                  <label className="text-sm font-medium">Public JWKS URL</label>
                  <Input readOnly value={jwksUrl} onFocus={(e) => e.target.select()} />
                </div>
                <div>
                  <label className="text-sm font-medium">Custom parameter</label>
                  <Input readOnly value={customParam} onFocus={(e) => e.target.select()} />
                </div>
                <p className="text-sm text-muted-foreground">
                  Register the platform at <a href={`${origin}/lti/admin/platforms`} target="_blank" rel="noreferrer" className="underline">/lti/admin/platforms</a> before launching.
                </p>
              </div>
            );
          })()}
          <AlertDialogFooter>
            <AlertDialogCancel>Close</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
