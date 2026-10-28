import { cn } from "@akashic-labs/ui";

export const DashboardHeader = ({
  className,
  ...props
}: React.ComponentProps<"header">) => {
  return (
    <header
      className={cn(
        "flex w-full flex-wrap items-center justify-between gap-4 py-2 md:gap-6 lg:gap-10",
        className,
      )}
      {...props}
    />
  );
};

export const DashboardHeaderTitle = ({
  className,
  ...props
}: React.ComponentProps<"h1">) => {
  return (
    <h1
      className={cn("text-3xl font-bold tracking-tighter", className)}
      {...props}
    />
  );
};

export const DashboardHeaderDescription = ({
  className,
  ...props
}: React.ComponentProps<"p">) => {
  return (
    <p
      className={cn("text-muted-foreground text-sm text-pretty", className)}
      {...props}
    />
  );
};
