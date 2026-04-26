"use client";

import { FormEvent, useState } from "react";

type Props = {
  disabled?: boolean;
  onSubmit: (value: string) => void;
};

export default function ActionOverlay({ disabled = false, onSubmit }: Props) {
  const [value, setValue] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <div className="absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/75 to-transparent p-4 md:p-8">
      <div className="mx-auto max-w-3xl rounded-2xl border border-mist/20 bg-ink/60 p-4 backdrop-blur-md">
        <form onSubmit={submit} className="flex gap-2">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={disabled}
            placeholder="What do you do?"
            className="flex-1 rounded-xl border border-mist/30 bg-black/40 px-4 py-3 text-sm text-mist placeholder:text-mist/50 outline-none focus:border-portal"
            autoFocus
          />
          <button
            type="submit"
            disabled={disabled}
            className="rounded-xl bg-portal px-4 py-3 text-sm font-medium text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
