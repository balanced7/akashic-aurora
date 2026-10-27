/** "Walk 01": the series number as the walks print it. */
export const walkLabel = (walk: number) =>
  `Walk ${String(walk).padStart(2, "0")}`;

/** Whole minutes to read, never zero. `timeToRead` is in milliseconds. */
export const minutesToRead = (timeToRead: number) =>
  Math.max(1, Math.ceil(timeToRead / 60_000));
