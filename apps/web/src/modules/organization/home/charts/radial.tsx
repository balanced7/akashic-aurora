"use client";

import { PolarGrid, RadialBar, RadialBarChart } from "recharts";

import { useTranslation } from "@akashic-labs/i18n";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@akashic-labs/ui-web/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@akashic-labs/ui-web/chart";
import { Icons } from "@akashic-labs/ui-web/icons";

import type { ChartConfig } from "@akashic-labs/ui-web/chart";

const chartData = [
  { browser: "chrome", visitors: 275, fill: "var(--chart-1)" },
  { browser: "safari", visitors: 200, fill: "var(--chart-2)" },
  { browser: "firefox", visitors: 187, fill: "var(--chart-3)" },
  { browser: "edge", visitors: 173, fill: "var(--chart-4)" },
  { browser: "opera", visitors: 90, fill: "var(--chart-5)" },
];

const chartConfig = {
  chrome: {
    label: "Chrome",
    color: "var(--chart-1)",
  },
  safari: {
    label: "Safari",
    color: "var(--chart-2)",
  },
  firefox: {
    label: "Firefox",
    color: "var(--chart-3)",
  },
  edge: {
    label: "Edge",
    color: "var(--chart-4)",
  },
  opera: {
    label: "Opera",
    color: "var(--chart-5)",
  },
} satisfies ChartConfig;

export function RadialChart() {
  const { t } = useTranslation(["common", "dashboard"]);
  return (
    <Card className="flex flex-col">
      <CardHeader className="items-center space-y-0.5 pb-0">
        <CardTitle className="text-xl">{t("chart.radial")}</CardTitle>
        <CardDescription>{t("chart.period")}</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 pb-0">
        <ChartContainer
          config={chartConfig}
          className="mx-auto aspect-square max-h-[250px]"
        >
          <RadialBarChart data={chartData} innerRadius={30} outerRadius={100}>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel nameKey="browser" />}
            />
            <PolarGrid gridType="circle" />
            <RadialBar dataKey="visitors" />
          </RadialBarChart>
        </ChartContainer>
      </CardContent>
      <CardFooter className="flex-col gap-2 text-sm">
        <div className="flex items-center gap-2 leading-none font-medium">
          {t("chart.trending")} <Icons.TrendingUp className="h-4 w-4" />
        </div>
        <div className="text-muted-foreground leading-none">
          {t("chart.showing")}
        </div>
      </CardFooter>
    </Card>
  );
}
