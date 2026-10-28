import history from "~/modules/marketing/content/generated/aurora-history.json";

/** Daily commit counts from the Aurora git log, drawn like a contribution graph. */

const CELL = 12;
const GAP = 3;
const DAY_MS = 86_400_000;

const levels = [
  "rgb(255 255 255 / 0.05)",
  "rgb(10 200 185 / 0.25)",
  "rgb(10 200 185 / 0.45)",
  "rgb(10 200 185 / 0.7)",
  "#0ac8b9",
];

const levelFor = (count: number) => {
  if (count === 0) return 0;
  if (count < 5) return 1;
  if (count < 20) return 2;
  if (count < 60) return 3;
  return 4;
};

export const CommitHeatmap = () => {
  const days = history.days as Record<string, number>;
  const start = new Date(`${history.firstCommit}T00:00:00Z`);
  const end = new Date(`${history.generatedAt}T00:00:00Z`);
  // Align the grid to the Sunday on or before the first commit.
  const gridStart = new Date(start.getTime() - start.getUTCDay() * DAY_MS);
  const totalDays =
    Math.round((end.getTime() - gridStart.getTime()) / DAY_MS) + 1;
  const weeks = Math.ceil(totalDays / 7);

  const cells = Array.from({ length: totalDays }, (_, index) => {
    const date = new Date(gridStart.getTime() + index * DAY_MS);
    const key = date.toISOString().slice(0, 10);
    const inRange = date >= start;
    return {
      key,
      count: inRange ? (days[key] ?? 0) : -1,
      week: Math.floor(index / 7),
      weekday: index % 7,
    };
  });

  const monthLabels = cells
    .filter((cell) => cell.weekday === 0 && cell.key.endsWith("-01") === false)
    .reduce<{ week: number; label: string }[]>((labels, cell) => {
      const label = new Date(`${cell.key}T00:00:00Z`).toLocaleString("en-US", {
        month: "short",
        timeZone: "UTC",
      });
      if (labels.at(-1)?.label !== label)
        labels.push({ week: cell.week, label });
      return labels;
    }, []);

  const width = weeks * (CELL + GAP);
  const height = 7 * (CELL + GAP) + 18;
  const busiest = Object.entries(days).sort((a, b) => b[1] - a[1])[0];

  return (
    <figure
      data-testid="commit-heatmap"
      className="mk-card flex flex-col gap-5 p-6 sm:p-8"
    >
      <div className="overflow-x-auto">
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${history.totalCommits} commits between ${history.firstCommit} and ${history.generatedAt}`}
        >
          {monthLabels.map((month) => (
            <text
              key={`${month.label}-${month.week}`}
              x={month.week * (CELL + GAP)}
              y={10}
              fontSize="10"
              fill="rgb(255 255 255 / 0.4)"
            >
              {month.label}
            </text>
          ))}
          {cells.map((cell) =>
            cell.count < 0 ? null : (
              <rect
                key={cell.key}
                x={cell.week * (CELL + GAP)}
                y={18 + cell.weekday * (CELL + GAP)}
                width={CELL}
                height={CELL}
                rx={2.5}
                fill={levels[levelFor(cell.count)]}
              >
                <title>{`${cell.key}: ${cell.count} commit${cell.count === 1 ? "" : "s"}`}</title>
              </rect>
            ),
          )}
        </svg>
      </div>
      <figcaption className="text-mk-faint flex flex-wrap items-center justify-between gap-4 text-[12.5px]">
        <span>
          {history.totalCommits.toLocaleString("en-US")} commits from{" "}
          {history.firstCommit} to {history.generatedAt}
          {busiest
            ? `. Busiest day: ${busiest[1]} commits on ${busiest[0]}.`
            : "."}
        </span>
        <span className="flex items-center gap-1.5">
          Less
          {levels.map((color) => (
            <span
              key={color}
              className="inline-block size-2.5 rounded-[2px]"
              style={{ background: color }}
            />
          ))}
          More
        </span>
      </figcaption>
    </figure>
  );
};
