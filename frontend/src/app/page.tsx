import { btn, subtext, card } from "@/lib/ui";
import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-4xl p-6 space-y-6">
      <h1 className="text-3xl font-semibold">Spotify Recs</h1>
      <p className={subtext}>Choose a flow</p>

      <div className={`${card} p-4`}>
        <div className="flex gap-3">
          <Link href="/search" className={btn.ghost}>
            Search
          </Link>
          <Link href="/recommend" className={btn.ghost}>
            Recommendations
          </Link>
        </div>
      </div>
    </main>
  );
}
