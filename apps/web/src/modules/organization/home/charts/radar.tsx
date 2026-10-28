"use client";

import dayjs from "dayjs";
import { TrendingUp } from "lucide-react";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart as RechartsRadarChart,
} from "recharts";

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

import type { ChartConfig } from "@akashic-labs/ui-web/chart";

const chartData = [
  { month: dayjs().month(0).format("MMMM"), desktop: 186, mobile: 80 },
  { month: dayjs().month(1).format("MMMM"), desktop: 305, mobile: 200 },
  { month: dayjs().month(2).format("MMMM"), desktop: 237, mobile: 120 },
  { month: dayjs().month(3).format("MMMM"), desktop: 73, mobile: 190 },
  { month: dayjs().month(4).format("MMMM"), desktop: 209, mobile: 130 },
  { month: dayjs().month(5).format("MMMM"), desktop: 214, mobile: 140 },
];

export function RadarChart() {
  const { t } = useTranslation(["common", "dashboard"]);

  const chartConfig = {
    desktop: {
      label: t("desktop"),
      color: "var(--chart-1)",
    },
    mobile: {
      label: t("mobile"),
      color: "var(--chart-4)",
    },
  } satisfies ChartConfig;

  return (
    <Card>
      <CardHeader className="items-center space-y-0.5 pb-4">
        <CardTitle className="text-xl">{t("chart.radar")}</CardTitle>
        <CardDescription>{t("chart.period")}</CardDescription>
      </CardHeader>
      <CardContent className="pb-0">
        <ChartContainer
          config={chartConfig}
          className="mx-auto aspect-square max-h-[250px]"
        >
          <RechartsRadarChart
            data={chartData}
            margin={{
              top: 10,
              right: 10,
              bottom: 10,
              left: 10,
            }}
          >
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent indicator="line" />}
            />
            <PolarAngleAxis
              dataKey="month"
              tick={({ x, y, textAnchor, index, ...props }) => {
                const data = chartData[index]!;

                return (
                  <text
                    x={x}
                    y={index === 0 ? Number(y) - 10 : y}
                    textAnchor={textAnchor}
                    fontSize={13}
                    fontWeight={500}
                    {...props}
                  >
                    <tspan className="fill-muted-foreground">
                      {data.desktop}
                    </tspan>
                    <tspan className="fill-muted-foreground">/</tspan>
                    <tspan className="fill-muted-foreground">
                      {data.mobile}
                    </tspan>
                    <tspan
                      x={x}
                      dy={"1rem"}
                      fontSize={12}
                      className="fill-muted-foreground"
                    >
                      {data.month}
                    </tspan>
                  </text>
                );
              }}
            />
            <PolarGrid />
            <Radar
              dataKey="desktop"
              fill={chartConfig.desktop.color}
              fillOpacity={0.6}
            />
            <Radar dataKey="mobile" fill={chartConfig.mobile.color} />
          </RechartsRadarChart>
        </ChartContainer>
      </CardContent>
      <CardFooter className="flex-col gap-2 text-sm">
        <div className="flex items-center gap-2 leading-none font-medium">
          {t("chart.trending")} <TrendingUp className="h-4 w-4" />
        </div>
        <div className="text-muted-foreground flex items-center gap-2 leading-none">
          {t("chart.period")}
        </div>
      </CardFooter>
    </Card>
  );
}
