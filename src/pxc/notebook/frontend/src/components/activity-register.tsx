"use client";

import { useEffect } from "react";
import { registerPxcActivity } from "@/lib/register-activity";

export function ActivityRegister() {
  useEffect(() => {
    registerPxcActivity();
  }, []);
  return null;
}
