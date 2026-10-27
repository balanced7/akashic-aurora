import { Button as ReactEmailButton } from "@react-email/components";
import { cva } from "class-variance-authority";

import { cn } from "@akashic-labs/ui";

import type { ButtonProps as ReactEmailButtonProps } from "@react-email/components";
import type { VariantProps } from "class-variance-authority";

export const buttonVariants = cva(
  "block rounded-md text-center text-sm font-medium whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        destructive: "bg-destructive text-destructive-foreground",
        outline: "border-input bg-background border",
        secondary: "bg-secondary text-secondary-foreground",
        link: "text-primary underline-offset-4",
      },
      size: {
        default: "px-4 py-2.5",
        sm: "rounded-md px-3",
        lg: "rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export type ButtonProps = ReactEmailButtonProps &
  VariantProps<typeof buttonVariants>;

export const Button = ({ variant, size, className, ...props }: ButtonProps) => {
  return (
    <ReactEmailButton
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
};
