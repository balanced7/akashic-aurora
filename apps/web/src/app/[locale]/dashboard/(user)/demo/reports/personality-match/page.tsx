"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@akashic-labs/ui-web/accordion";
import { Avatar, AvatarFallback } from "@akashic-labs/ui-web/avatar";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@akashic-labs/ui-web/card";
import { Icons } from "@akashic-labs/ui-web/icons";

import { PageNavigation } from "./components/page-navigation";

export default function RelationshipComparison() {
  const harmonyScore = 82;

  const bigFiveData = [
    { trait: "Extroversion", alex: 72, sam: 45 },
    { trait: "Openness", alex: 88, sam: 91 },
    { trait: "Conscientiousness", alex: 65, sam: 82 },
    { trait: "Agreeableness", alex: 78, sam: 88 },
    { trait: "Emotional Stability", alex: 70, sam: 58 },
  ];

  const sharedStrengths = [
    {
      title: "Value Alignment",
      description: "Both prioritize personal growth and authenticity",
    },
    {
      title: "Shared Interests",
      description: "Deep appreciation for creativity and exploration",
    },
    {
      title: "Emotional Intelligence",
      description: "High mutual awareness and empathy",
    },
    {
      title: "Growth Mindset",
      description: "Commitment to continuous learning together",
    },
  ];

  const growthOpportunities = [
    {
      title: "Conflict Resolution Speed",
      description: "Different pacing in processing disagreements",
    },
    {
      title: "Social Battery",
      description: "Varying energy levels in social situations",
    },
    {
      title: "Decision Making",
      description: "Alex prefers quick choices, Sam needs more time",
    },
    {
      title: "Communication Timing",
      description: "Different preferences for when to discuss topics",
    },
  ];

  const coachingInsights = [
    {
      title: "When Sam Gets Quiet",
      content:
        "Alex, when Sam withdraws during tension, this is their processing mode. Give 30-60 minutes of space before checking in. Sam, communicate this need: 'I need some time to think, can we revisit this in an hour?'",
    },
    {
      title: "Social Energy Balance",
      content:
        "Plan social events with built-in downtime. Alex can attend the full event while Sam takes a breather midway. Create a code word when Sam needs to leave early without awkwardness.",
    },
    {
      title: "Decision Making Harmony",
      content:
        "For small decisions, trust Alex's instinct. For big decisions, set a 48-hour reflection period for Sam. Create three tiers: instant decisions, 24-hour decisions, and major decisions requiring joint planning sessions.",
    },
    {
      title: "Leveraging Your Openness",
      content:
        "Both score high on Openness—use this strength! Schedule monthly 'exploration dates' trying new experiences together. This shared trait is your superpower for keeping the relationship fresh and exciting.",
    },
  ];

  return (
    <div className="relative min-h-screen w-full">
      <PageNavigation />

      {/* Hero Section */}
      <section id="hero" className="relative overflow-hidden py-12 md:py-20">
        <div className="mx-auto w-full max-w-6xl px-4">
          <div className="mb-8 text-center">
            <h1 className="text-foreground mb-3 text-4xl font-semibold tracking-tight md:text-5xl">
              Personality Match
            </h1>
            <p className="text-muted-foreground text-lg">
              A Akashic Labs Report to help you understand your unique dynamic
              through the lens of personality science.
            </p>
          </div>

          {/* Comparison Hero */}
          <div className="grid grid-cols-1 items-center gap-6 md:grid-cols-3">
            {/* Person A - Alex */}
            <Card className="border-primary/20 bg-white dark:bg-white/20">
              <CardHeader className="text-center">
                <Avatar className="border-primary/30 mx-auto mb-4 h-24 w-24 border-4">
                  <AvatarFallback className="bg-primary text-primary-foreground text-2xl font-bold">
                    A
                  </AvatarFallback>
                </Avatar>
                <CardTitle className="text-2xl">Alex</CardTitle>
                <CardDescription>The Visionary</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-center text-sm">
                <div className="flex items-center justify-center gap-2">
                  <Icons.Zap className="text-secondary h-4 w-4" />
                  <span className="text-muted-foreground">
                    Quick Decision Maker
                  </span>
                </div>
                <div className="flex items-center justify-center gap-2">
                  <Icons.TrendingUp className="text-secondary h-4 w-4" />
                  <span className="text-muted-foreground">High Energy</span>
                </div>
              </CardContent>
            </Card>

            {/* Center Harmony Score */}
            <div className="order-first md:order-none">
              <Card className="border-primary/30 bg-white shadow-lg dark:bg-white/20">
                <CardContent className="flex flex-col items-center justify-center py-8">
                  <Icons.Sparkles className="text-primary mb-4 h-8 w-8" />
                  <div className="text-center">
                    <p className="text-muted-foreground mb-2 text-sm font-medium tracking-wider uppercase">
                      Harmony Score
                    </p>
                    <div className="relative mb-4">
                      <svg className="h-32 w-32 -rotate-90 transform">
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="currentColor"
                          strokeWidth="8"
                          fill="none"
                          className="text-muted/30"
                        />
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="currentColor"
                          strokeWidth="8"
                          fill="none"
                          strokeDasharray={`${2 * Math.PI * 56}`}
                          strokeDashoffset={`${2 * Math.PI * 56 * (1 - harmonyScore / 100)}`}
                          className="text-primary transition-all duration-1000"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-foreground text-4xl font-bold">
                          {harmonyScore}%
                        </span>
                      </div>
                    </div>
                    <p className="text-muted-foreground text-sm">
                      Strong Compatibility
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Person B - Sam */}
            <Card className="border-secondary/20 bg-white dark:bg-white/20">
              <CardHeader className="text-center">
                <Avatar className="border-secondary/30 mx-auto mb-4 h-24 w-24 border-4">
                  <AvatarFallback className="bg-secondary text-secondary-foreground text-2xl font-bold">
                    S
                  </AvatarFallback>
                </Avatar>
                <CardTitle className="text-2xl">Sam</CardTitle>
                <CardDescription>The Supporter</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-center text-sm">
                <div className="flex items-center justify-center gap-2">
                  <Icons.Heart className="text-primary h-4 w-4" />
                  <span className="text-muted-foreground">
                    Thoughtful Processor
                  </span>
                </div>
                <div className="flex items-center justify-center gap-2">
                  <Icons.MessageCircle className="text-primary h-4 w-4" />
                  <span className="text-muted-foreground">Deep Listener</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Quick Stats */}
      <section id="quick-stats" className="w-full px-4 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-3xl">
            <p className="text-primary mb-3 text-sm font-semibold tracking-wider uppercase">
              At a Glance
            </p>
            <h2 className="mb-4 text-3xl font-semibold text-balance md:text-4xl">
              <span className="from-primary via-primary/90 to-primary/60 bg-gradient-to-r bg-clip-text font-semibold text-transparent">
                Your Relationship DNA.
              </span>{" "}
              <span className="text-foreground">Decoded.</span>
            </h2>
            <p className="text-muted-foreground text-base leading-relaxed">
              Every relationship has a unique signature. These core metrics
              reveal the foundation of your connection—from how you communicate
              to the dynamic that makes you{" "}
              <span className="text-foreground font-semibold">
                uniquely compatible
              </span>
              .
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            <Card className="border-accent/30 bg-white dark:bg-white/20">
              <CardHeader>
                <Icons.Heart className="text-primary mb-2 h-8 w-8" />
                <CardTitle>Core Relationship Type</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-foreground text-2xl font-semibold">
                  Romantic
                </p>
                <p className="text-muted-foreground mt-1 text-sm">
                  Deep emotional connection
                </p>
              </CardContent>
            </Card>

            <Card className="border-primary/30 bg-white dark:bg-white/20">
              <CardHeader>
                <Icons.Sparkles className="text-secondary mb-2 h-8 w-8" />
                <CardTitle>Primary Dynamic</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-foreground text-2xl font-semibold">
                  Visionary & Supporter
                </p>
                <p className="text-muted-foreground mt-1 text-sm">
                  Complementary partnership
                </p>
              </CardContent>
            </Card>

            <Card className="border-secondary/30 bg-white dark:bg-white/20">
              <CardHeader>
                <Icons.MessageCircle className="text-primary mb-2 h-8 w-8" />
                <CardTitle>Communication Style</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-foreground text-2xl font-semibold">
                  Open & Reflective
                </p>
                <p className="text-muted-foreground mt-1 text-sm">
                  Balanced dialogue
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Personality Deep-Dive */}
      <section id="personality" className="w-full px-4 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-3xl">
            <p className="text-secondary mb-3 text-sm font-semibold tracking-wider uppercase">
              Personality Science
            </p>
            <h2 className="mb-4 text-3xl font-semibold text-balance md:text-4xl">
              <span className="text-foreground">The traits that shape</span>{" "}
              <span className="bg-gradient-to-r from-green-600 via-green-600/90 to-emerald-500 bg-clip-text font-semibold text-transparent">
                who you are.
              </span>
            </h2>
            <p className="text-muted-foreground text-base leading-relaxed">
              Using the gold-standard Big Five personality model, we map where
              you align and where you differ. Understanding these dimensions
              helps you{" "}
              <span className="text-foreground font-semibold">
                appreciate your differences
              </span>{" "}
              rather than fight them.
            </p>
          </div>
          <Card className="bg-white dark:bg-white/20">
            <CardHeader>
              <CardTitle className="text-center text-3xl">
                Personality Deep-Dive
              </CardTitle>
              <CardDescription className="text-center">
                The Big Five Traits Comparison
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              {bigFiveData.map((item) => (
                <div key={item.trait} className="space-y-3">
                  <h3 className="text-foreground text-lg font-semibold">
                    {item.trait}
                  </h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    {/* Alex */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground font-medium">
                          Alex
                        </span>
                        <span className="text-foreground font-semibold">
                          {item.alex}%
                        </span>
                      </div>
                      <div className="bg-muted h-3 w-full overflow-hidden rounded-full">
                        <div
                          className="from-primary to-primary/70 h-full bg-gradient-to-r transition-all duration-1000"
                          style={{ width: `${item.alex}%` }}
                        />
                      </div>
                    </div>

                    {/* Sam */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground font-medium">
                          Sam
                        </span>
                        <span className="text-foreground font-semibold">
                          {item.sam}%
                        </span>
                      </div>
                      <div className="bg-muted h-3 w-full overflow-hidden rounded-full">
                        <div
                          className="from-secondary to-secondary/70 h-full bg-gradient-to-r transition-all duration-1000"
                          style={{ width: `${item.sam}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Friction & Flow Grid */}
      <section id="friction-flow" className="w-full px-4 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-3xl">
            <p className="text-warning mb-3 text-sm font-semibold tracking-wider uppercase">
              The Full Picture
            </p>
            <h2 className="mb-4 text-3xl font-semibold text-balance md:text-4xl">
              <span className="bg-gradient-to-r from-green-600 via-green-600/90 to-emerald-500 bg-clip-text font-semibold text-transparent">
                Where you shine.
              </span>{" "}
              <span className="text-foreground">Where you grow.</span>
            </h2>
            <p className="text-muted-foreground text-base leading-relaxed">
              Real compatibility isn't about being the same—it's about knowing
              where you{" "}
              <span className="text-success font-semibold">
                complement each other
              </span>{" "}
              and where you need{" "}
              <span className="text-warning font-semibold">
                intentional care
              </span>
              . Both matter equally.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Where You Shine */}
            <Card className="border-success/30 bg-white dark:bg-white/20">
              <CardHeader>
                <CardTitle className="text-success flex items-center gap-2">
                  <Icons.CheckCircle2 className="h-6 w-6" />
                  Where You Shine
                </CardTitle>
                <CardDescription>
                  Your natural strengths together
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {sharedStrengths.map((strength, index) => (
                  <div
                    key={index}
                    className="bg-success/5 flex gap-3 rounded-lg p-4"
                  >
                    <Icons.CheckCircle2 className="text-success mt-0.5 h-5 w-5 flex-shrink-0" />
                    <div>
                      <h4 className="text-foreground mb-1 font-semibold">
                        {strength.title}
                      </h4>
                      <p className="text-muted-foreground text-sm">
                        {strength.description}
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Growth Opportunities */}
            <Card className="border-warning/30 bg-white dark:bg-white/20">
              <CardHeader>
                <CardTitle className="text-warning flex items-center gap-2">
                  <Icons.AlertCircle className="h-6 w-6" />
                  Growth Opportunities
                </CardTitle>
                <CardDescription>Areas to navigate mindfully</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {growthOpportunities.map((opportunity, index) => (
                  <div
                    key={index}
                    className="bg-warning/5 flex gap-3 rounded-lg p-4"
                  >
                    <Icons.AlertCircle className="text-warning mt-0.5 h-5 w-5 flex-shrink-0" />
                    <div>
                      <h4 className="text-foreground mb-1 font-semibold">
                        {opportunity.title}
                      </h4>
                      <p className="text-muted-foreground text-sm">
                        {opportunity.description}
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Coaching Insights */}
      <section id="coaching" className="w-full px-4 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 max-w-3xl">
            <p className="text-primary mb-3 text-sm font-semibold tracking-wider uppercase">
              Your Action Plan
            </p>
            <h2 className="mb-4 text-3xl font-semibold text-balance md:text-4xl">
              <span className="text-foreground">From insight to</span>{" "}
              <span className="from-primary via-primary/90 to-primary/60 bg-gradient-to-r bg-clip-text font-semibold text-transparent">
                action.
              </span>
            </h2>
            <p className="text-muted-foreground text-base leading-relaxed">
              Data is powerful, but{" "}
              <span className="text-foreground font-semibold">
                guidance makes it transformative
              </span>
              . These coaching insights are tailored to your specific
              patterns—so you can turn understanding into real change.
            </p>
          </div>
          <Card className="border-primary/30 bg-white dark:bg-white/20">
            <CardHeader>
              <CardTitle className="text-center text-3xl">
                Resolution Roadmap
              </CardTitle>
              <CardDescription className="text-center">
                Practical strategies for your specific dynamic
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="w-full">
                {coachingInsights.map((insight, index) => (
                  <AccordionItem key={index} value={`item-${index}`}>
                    <AccordionTrigger className="hover:text-primary text-left">
                      <span className="flex items-center gap-2">
                        <Icons.Sparkles className="text-primary h-5 w-5" />
                        {insight.title}
                      </span>
                    </AccordionTrigger>
                    <AccordionContent className="text-muted-foreground leading-relaxed">
                      {insight.content}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Call to Action */}
      <section id="cta" className="w-full px-4 py-12 pb-24 lg:pb-20">
        <div className="mx-auto max-w-6xl">
          <Card className="border-primary/30 bg-white dark:bg-white/20">
            <CardHeader className="text-center">
              <Icons.Calendar className="text-primary mx-auto mb-4 h-12 w-12" />
              <CardTitle className="text-3xl">
                Ready to Deepen Your Connection?
              </CardTitle>
              <CardDescription className="mt-2 text-base">
                Get personalized guidance from a relationship coach who
                understands your unique dynamic
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-4">
              <div className="grid w-full max-w-2xl gap-4 text-center md:grid-cols-3">
                <div className="bg-background/50 rounded-lg p-4">
                  <Icons.CheckCircle2 className="text-success mx-auto mb-2 h-6 w-6" />
                  <p className="text-sm font-medium">
                    Personalized Action Plan
                  </p>
                </div>
                <div className="bg-background/50 rounded-lg p-4">
                  <Icons.Heart className="text-primary mx-auto mb-2 h-6 w-6" />
                  <p className="text-sm font-medium">Evidence-Based Approach</p>
                </div>
                <div className="bg-background/50 rounded-lg p-4">
                  <Icons.Sparkles className="text-secondary mx-auto mb-2 h-6 w-6" />
                  <p className="text-sm font-medium">
                    Confidential & Supportive
                  </p>
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-center">
              <Button
                size="lg"
                className="bg-primary hover:bg-primary/90 text-primary-foreground px-8"
              >
                Book a 15-Minute Sync
              </Button>
            </CardFooter>
          </Card>
        </div>
      </section>
    </div>
  );
}
