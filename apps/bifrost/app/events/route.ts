const BACKEND = process.env.BIFROST_API ?? "http://127.0.0.1:8787";

export const dynamic = "force-dynamic";

/** Pipe the bus SSE stream through unbuffered; the client's EventSource reconnects on close. */
export async function GET(req: Request) {
  const qs = new URL(req.url).search;
  try {
    const upstream = await fetch(`${BACKEND}/events${qs}`, {
      signal: req.signal,
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") ?? "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return new Response("bifrost console backend unreachable", { status: 502 });
  }
}
