"use client";

import { useOnlineStatus } from "@/hooks/use-online-status";

export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <div className="bg-yellow-100 border-b border-yellow-300 text-yellow-900 text-sm px-6 py-2">
      You are offline. Changes will be pushed when you reconnect.
    </div>
  );
}
