"use client";

import { useEffect } from "react";
import { registerXplActivity } from "@/lib/register-activity";

export function ActivityRegister() {
  useEffect(() => {
    registerXplActivity();
  }, []);
  return null;
}
