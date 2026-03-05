"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

type AddFormProps = { onAdd: (value: string) => Promise<void>; placeholder?: string; options?: string[] };

export function AddForm({ onAdd, placeholder = "Title…", options }: AddFormProps) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    setLoading(true);
    await onAdd(value.trim());
    setValue("");
    setLoading(false);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 mt-4">
      {options ? (
        <Select value={value} onValueChange={(v) => setValue(v ?? "")}>
          <SelectTrigger className="flex-1"><SelectValue placeholder="Select…" /></SelectTrigger>
          <SelectContent>
            {options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
          </SelectContent>
        </Select>
      ) : (
        <Input value={value} onChange={(e) => setValue(e.target.value)} placeholder={placeholder} className="flex-1" />
      )}
      <Button type="submit" disabled={loading || !value.trim()}>Add</Button>
    </form>
  );
}
