export type AllowedPropertyValues = string | number | boolean;

type TrackFunction = (
  event: string,
  data?: Record<string, AllowedPropertyValues>,
) => void;

export interface AnalyticsProviderClientStrategy {
  Provider: ({ children }: { children: React.ReactNode }) => React.ReactNode;
  track: TrackFunction;
}

export interface AnalyticsProviderServerStrategy {
  track: TrackFunction;
}
