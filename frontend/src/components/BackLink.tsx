"use client";
import Link from "next/link";
import { btn } from "@/lib/ui";

export default function BackLink() {
  return (
    <Link href="/" className={btn.ghost}>
      ← Home
    </Link>
  );
}