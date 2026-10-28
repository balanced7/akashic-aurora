import { getMetadata } from "~/lib/metadata";
import { AIDemo } from "~/modules/marketing/ai-demo";

export const generateMetadata = getMetadata({
  title: "ai",
  description: "marketing:ai.description",
});

export default function AI() {
  return <AIDemo />;
}
