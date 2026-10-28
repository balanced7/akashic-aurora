"use client";

import { useCallback, useEffect, useState } from "react";

import type { SkillNodeMedia } from "../core/types";

interface MilestoneMediaProps {
  media: SkillNodeMedia;
  title: string;
  className?: string;
  /** Compact thumb for canvas nodes */
  compact?: boolean;
}

/**
 * Prefers video when provided; falls back to still image on error,
 * missing video, or when the browser cannot play the clip.
 */
export function MilestoneMedia({
  media,
  title,
  className = "",
  compact = false,
}: MilestoneMediaProps) {
  const [useVideo, setUseVideo] = useState(
    () => Boolean(media.video) && !compact,
  );
  const alt = media.alt ?? title;

  const showImage = useCallback(() => {
    setUseVideo(false);
  }, []);

  // Reset when media changes; canvas thumbs stay on stills.
  useEffect(() => {
    setUseVideo(Boolean(media.video) && !compact);
  }, [media.video, media.image, compact]);

  const frame = compact
    ? "aspect-[3/2] w-full overflow-hidden rounded-md"
    : "aspect-[3/2] w-full overflow-hidden rounded-lg";

  return (
    <div className={`${frame} bg-zinc-200 ${className}`}>
      {useVideo && media.video ? (
        <video
          key={media.video}
          className="h-full w-full object-cover"
          src={media.video}
          poster={media.image}
          muted
          playsInline
          autoPlay={!compact}
          loop
          controls={!compact}
          preload={compact ? "metadata" : "auto"}
          aria-label={alt}
          onError={showImage}
          onAbort={showImage}
        />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element -- static public posters
        <img
          src={media.image}
          alt={alt}
          className="h-full w-full object-cover"
          loading="lazy"
          draggable={false}
        />
      )}
    </div>
  );
}
