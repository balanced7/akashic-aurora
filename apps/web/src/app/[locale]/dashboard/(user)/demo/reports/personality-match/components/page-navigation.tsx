"use client";

import React from "react";
import { useState, useEffect } from "react";

import { cn } from "@akashic-labs/ui";
import { Icons } from "@akashic-labs/ui-web/icons";

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { id: "hero", label: "Overview", icon: <Icons.Home className="size-4" /> },
  {
    id: "quick-stats",
    label: "Quick Stats",
    icon: <Icons.Zap className="size-4" />,
  },
  {
    id: "personality",
    label: "Personality",
    icon: <Icons.Brain className="size-4" />,
  },
  {
    id: "friction-flow",
    label: "Friction & Flow",
    icon: <Icons.Scale className="size-4" />,
  },
  {
    id: "coaching",
    label: "Action Plan",
    icon: <Icons.Lightbulb className="size-4" />,
  },
  {
    id: "cta",
    label: "Book Coaching",
    icon: <Icons.Calendar className="size-4" />,
  },
];

export function PageNavigation() {
  const [activeSection, setActiveSection] = useState("hero");

  useEffect(() => {
    const handleScroll = () => {
      const sections = navItems.map((item) => document.getElementById(item.id));
      const scrollPosition = window.scrollY + window.innerHeight / 3;

      for (let i = sections.length - 1; i >= 0; i--) {
        const section = sections[i];
        const item = navItems[i];
        if (section && item && section.offsetTop <= scrollPosition) {
          setActiveSection(item.id);
          break;
        }
      }
    };

    window.addEventListener("scroll", handleScroll);
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      const yOffset = -20;
      const y =
        element.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: "smooth" });
    }
  };

  return (
    <>
      {/* Desktop Navigation - Fixed to Right Side of Viewport */}
      <nav className="hidden lg:fixed lg:top-1/2 lg:right-4 lg:z-10 lg:flex lg:-translate-y-1/2 lg:flex-col lg:gap-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => scrollToSection(item.id)}
            className={cn(
              "group relative flex size-7 items-center justify-center rounded-md transition-all duration-200",
              activeSection === item.id
                ? "bg-primary text-primary-foreground shadow-lg"
                : "bg-card/80 text-muted-foreground hover:bg-card hover:text-foreground border-border border backdrop-blur-sm",
            )}
            aria-label={item.label}
          >
            {item.icon}
            {/* Tooltip on hover - appears on left side since nav is on right */}
            <span className="bg-foreground text-background pointer-events-none absolute right-full mr-3 rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap opacity-0 transition-opacity group-hover:opacity-100">
              {item.label}
            </span>
          </button>
        ))}
      </nav>

      {/* Mobile Navigation - Bottom Bar */}
      <nav className="bg-card/95 border-border fixed right-0 bottom-0 left-0 z-50 border-t shadow-lg backdrop-blur-md lg:hidden">
        <div className="flex items-center justify-around px-2 py-3">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => scrollToSection(item.id)}
              className={cn(
                "flex min-w-[60px] flex-col items-center gap-1 rounded-lg px-3 py-2 transition-all duration-200",
                activeSection === item.id
                  ? "text-primary"
                  : "text-muted-foreground",
              )}
              aria-label={item.label}
            >
              <span
                className={cn(
                  "transition-transform duration-200",
                  activeSection === item.id && "scale-110",
                )}
              >
                {item.icon}
              </span>
              <span className="text-center text-[10px] leading-tight font-medium">
                {item.label.split(" ")[0]}
              </span>
            </button>
          ))}
        </div>
      </nav>
    </>
  );
}
