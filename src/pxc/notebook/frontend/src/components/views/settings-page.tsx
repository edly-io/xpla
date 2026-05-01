"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getApiToken, regenerateApiToken } from "@/lib/api";

export function SettingsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getApiToken().then((r) => setToken(r.token));
  }, []);

  async function handleRegenerate() {
    const r = await regenerateApiToken();
    setToken(r.token);
    setCopied(false);
  }

  function handleCopy() {
    if (!token) return;
    navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="p-6 max-w-xl">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <section>
        <h2 className="text-lg font-semibold mb-2">API Token</h2>
        <p className="text-sm text-muted-foreground mb-3">
          Use this token to authenticate API requests from external tools (e.g., AI agents).
          Include it as <code>Authorization: Bearer &lt;token&gt;</code>.
        </p>
        <div className="flex gap-2 mb-3">
          <Input readOnly value={token ?? "Loading…"} onFocus={(e) => e.target.select()} className="font-mono text-xs" />
          <Button variant="outline" onClick={handleCopy} disabled={!token}>
            {copied ? "Copied!" : "Copy"}
          </Button>
        </div>
        <Button variant="destructive" size="sm" onClick={handleRegenerate}>
          Regenerate
        </Button>
        <p className="text-xs text-muted-foreground mt-2">
          Regenerating invalidates the current token immediately.
        </p>
      </section>
    </div>
  );
}
