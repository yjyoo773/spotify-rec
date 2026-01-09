import { Suspense } from "react";
import RecommendClient from "./RecommendClient";

export default function RecommendPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading…</div>}>
      <RecommendClient />
    </Suspense>
  );
}
