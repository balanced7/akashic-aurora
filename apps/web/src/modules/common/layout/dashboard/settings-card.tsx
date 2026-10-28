import { cva } from "class-variance-authority";
import * as React from "react";
import { createContext, useContext } from "react";

import { cn } from "@akashic-labs/ui";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@akashic-labs/ui-web/card";

import type { VariantProps } from "class-variance-authority";

const settingsCardVariant = cva("bg-background h-fit w-full overflow-hidden", {
  variants: {
    variant: {
      default: "dark:border-input",
      destructive: "border-destructive/25",
    },
  },
  defaultVariants: {
    variant: "default",
  },
});

const SettingsCardContext = createContext<
  {
    disabled: boolean;
  } & VariantProps<typeof settingsCardVariant>
>({
  disabled: false,
  variant: "default",
});

const SettingsCard = ({
  className,
  variant,
  disabled = false,
  ...props
}: React.ComponentProps<typeof Card> &
  VariantProps<typeof settingsCardVariant> & { disabled?: boolean }) => (
  <SettingsCardContext.Provider value={{ disabled, variant }}>
    <Card
      className={cn(
        settingsCardVariant({ variant: disabled ? "default" : variant }),
        "pb-0",
        {
          "text-muted-foreground cursor-not-allowed": disabled,
        },
        className,
      )}
      {...props}
    />
  </SettingsCardContext.Provider>
);

const SettingsCardHeader = CardHeader;

const SettingsCardTitle = ({
  className,
  ...props
}: React.ComponentProps<typeof CardTitle>) => (
  <CardTitle className={cn("text-xl", className)} {...props} />
);

const SettingsCardDescription = ({
  className,
  ...props
}: React.ComponentProps<typeof CardDescription>) => {
  const { disabled } = useContext(SettingsCardContext);

  return (
    <CardDescription
      className={cn(
        "pb-1.5 text-sm",
        {
          "text-foreground": !disabled,
        },
        className,
      )}
      {...props}
    />
  );
};

const SettingsCardContent = ({
  className,
  ...props
}: React.ComponentProps<typeof CardContent>) => {
  return <CardContent className={cn("-mt-4", className)} {...props} />;
};

const settingsCardFooterVariant = cva(
  "flex min-h-14 cursor-auto justify-between gap-10 border-t py-3 text-sm leading-tight [.border-t]:pt-3",
  {
    variants: {
      variant: {
        default: "bg-accent text-muted-foreground dark:bg-accent/75",
        destructive:
          "border-t-destructive/25 bg-destructive/15 dark:bg-destructive/20 border-t",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

const SettingsCardFooter = ({
  className,
  ...props
}: React.ComponentProps<typeof CardFooter>) => {
  const { variant, disabled } = useContext(SettingsCardContext);
  return (
    <CardFooter
      className={cn(
        settingsCardFooterVariant({ variant: disabled ? "default" : variant }),
        className,
      )}
      {...props}
    />
  );
};

export {
  SettingsCard,
  SettingsCardHeader,
  SettingsCardContent,
  SettingsCardFooter,
  SettingsCardTitle,
  SettingsCardDescription,
};
