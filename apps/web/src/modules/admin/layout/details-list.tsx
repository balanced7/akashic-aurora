import { cn } from "@akashic-labs/ui";

export const DetailsList = ({
  className,
  ...props
}: React.ComponentProps<"ul">) => {
  return (
    <ul
      className={cn(
        "xl:*:px- -m-px grid grid-cols-1 gap-y-8 @lg/details:grid-cols-2 @lg/details:gap-y-0 @3xl/details:grid-cols-3",
        className,
      )}
      {...props}
    />
  );
};

export const DetailsListItem = ({
  className,
  ...props
}: React.ComponentProps<"li">) => (
  <li
    className={cn(
      "px-1 @lg/details:border @lg/details:px-6 @lg/details:py-8 @3xl/details:px-8 @3xl/details:py-10 [&:not(:first-child)]:-ms-px [&:not(:first-child)]:-mt-px",
      className,
    )}
    {...props}
  />
);
