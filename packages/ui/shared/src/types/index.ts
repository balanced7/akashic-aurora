export const ThemeMode = {
  SYSTEM: "system",
  LIGHT: "light",
  DARK: "dark",
} as const;

export const ThemeColor = {
  ORANGE: "orange",
  ROSE: "rose",
  RED: "red",
  YELLOW: "yellow",
  AKASHIC_LABS: "akashic-labs",
  GRAY: "gray",
  STONE: "stone",
  GREEN: "green",
  BLUE: "blue",
  VIOLET: "violet",
} as const;

export const DEFAULT_BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type ThemeColor = (typeof ThemeColor)[keyof typeof ThemeColor];
export type ThemeMode = (typeof ThemeMode)[keyof typeof ThemeMode];

export interface ThemeConfig {
  mode: ThemeMode;
  color: ThemeColor;
}
