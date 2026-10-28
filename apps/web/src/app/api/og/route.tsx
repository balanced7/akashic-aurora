import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import path from "node:path";

/** Per-page social cards in the site's style: /api/og?title=...&eyebrow=... */
export const runtime = "nodejs";

const SIZE = { width: 1200, height: 630 };
const MAX_TITLE = 90;

const fontDir = path.join(process.cwd(), "src/assets/fonts");
const fontsPromise = Promise.all([
  readFile(path.join(fontDir, "BricolageGrotesque-Bold.ttf")),
  readFile(path.join(fontDir, "BricolageGrotesque-Light.ttf")),
  readFile(path.join(fontDir, "ChakraPetch-SemiBold.ttf")),
]);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const title = (searchParams.get("title") ?? "A home for your agents").slice(
    0,
    MAX_TITLE,
  );
  const eyebrow = (searchParams.get("eyebrow") ?? "Akashic Aurora").slice(
    0,
    40,
  );
  const [bold, light, hud] = await fontsPromise;
  const titleSize = title.length > 60 ? 64 : title.length > 36 ? 76 : 92;

  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "64px 72px",
        background: "#000",
        color: "#fff",
        position: "relative",
        fontFamily: "Bricolage",
      }}
    >
      {/* Aurora sky */}
      <div
        style={{
          position: "absolute",
          top: -220,
          right: -160,
          width: 900,
          height: 640,
          borderRadius: 9999,
          background:
            "radial-gradient(circle, rgba(10,200,185,0.55), rgba(10,200,185,0) 65%)",
          display: "flex",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 60,
          right: -220,
          width: 600,
          height: 520,
          borderRadius: 9999,
          background:
            "radial-gradient(circle, rgba(200,170,110,0.35), rgba(200,170,110,0) 65%)",
          display: "flex",
        }}
      />
      {/* HUD corners */}
      <div
        style={{
          position: "absolute",
          top: 28,
          left: 28,
          width: 26,
          height: 26,
          borderTop: "2px solid #c8aa6e",
          borderLeft: "2px solid #c8aa6e",
          display: "flex",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 28,
          right: 28,
          width: 26,
          height: 26,
          borderBottom: "2px solid #c8aa6e",
          borderRight: "2px solid #c8aa6e",
          display: "flex",
        }}
      />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: -0.8,
        }}
      >
        <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
          <path
            d="M16 1.5 29 9v14L16 30.5 3 23V9L16 1.5Z"
            stroke="#c8aa6e"
            strokeWidth="1.6"
          />
          <path
            d="M16 7.5 23.5 12v8L16 24.5 8.5 20v-8L16 7.5Z"
            fill="#0ac8b9"
          />
        </svg>
        Akashic Labs
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            fontFamily: "Chakra",
            fontSize: 20,
            letterSpacing: 4,
            color: "#c8aa6e",
            textTransform: "uppercase",
          }}
        >
          <div
            style={{
              width: 11,
              height: 11,
              background: "#0ac8b9",
              transform: "rotate(45deg)",
              display: "flex",
            }}
          />
          {eyebrow}
        </div>
        <div
          style={{
            display: "flex",
            fontSize: titleSize,
            lineHeight: 1,
            letterSpacing: -3,
            fontWeight: 700,
            maxWidth: 980,
          }}
        >
          {title}
        </div>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          fontSize: 22,
          color: "rgba(255,255,255,0.6)",
          fontWeight: 300,
        }}
      >
        <div style={{ display: "flex" }}>Aurora · a home for your agents</div>
        <div style={{ display: "flex" }}>open source · Apache-2.0</div>
      </div>
    </div>,
    {
      ...SIZE,
      fonts: [
        { name: "Bricolage", data: bold, weight: 700, style: "normal" },
        { name: "Bricolage", data: light, weight: 300, style: "normal" },
        { name: "Chakra", data: hud, weight: 600, style: "normal" },
      ],
      headers: {
        "Cache-Control": "public, max-age=86400, s-maxage=604800, immutable",
      },
    },
  );
}
