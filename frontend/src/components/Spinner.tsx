"use client";

export default function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-gray-600">
      <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" aria-hidden="true">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
      </svg>
      {label ? <span className="text-sm">{label}</span> : null}
    </div>
  );
}
