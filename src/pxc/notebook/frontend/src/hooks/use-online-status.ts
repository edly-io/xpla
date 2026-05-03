"use client";

import { useEffect, useState } from "react";

export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const handler = (e: Event) => {
      setOnline((e as CustomEvent).detail.connected);
    };
    window.addEventListener("pxc:connection", handler);
    return () => window.removeEventListener("pxc:connection", handler);
  }, []);
  return online;
}
