import React, { memo } from "react";

interface AuthHeaderProps {
  readonly title: React.ReactNode;
  readonly description: React.ReactNode;
}

export const AuthHeader = memo<AuthHeaderProps>(({ title, description }) => {
  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tighter">{title}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{description}</p>
    </div>
  );
});

AuthHeader.displayName = "AuthHeader";
