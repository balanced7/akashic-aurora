"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { marked } from "marked";
import { useState } from "react";

import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";
import { ScrollArea } from "@akashic-labs/ui-web/scroll-area";
import { Textarea } from "@akashic-labs/ui-web/textarea";

import { api } from "~/lib/api/client";

import type { KeyboardEvent } from "react";

const EXAMPLES = [
  {
    icon: Icons.Globe2,
    prompt: "ai.prompt.history",
  },
  {
    icon: Icons.GraduationCap,
    prompt: "ai.prompt.capitals",
  },
  {
    icon: Icons.Atom,
    prompt: "ai.prompt.quantum",
  },
  {
    icon: Icons.Brain,
    prompt: "ai.prompt.realWorld",
  },
] as const;

export const AIDemo = () => {
  const { t } = useTranslation("marketing");
  const [input, setInput] = useState("");
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: api.ai.chat.$url().toString(),
    }),
  });

  const messagesToDisplay = messages.filter((message) =>
    ["assistant", "user"].includes(message.role),
  );

  const isLoading = ["submitted", "streaming"].includes(status);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage({ text: input });
      setInput("");
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl grow flex-col items-center justify-between gap-4 self-stretch">
      <ScrollArea className="w-full grow">
        <div className="prose dark:prose-invert flex flex-col gap-2">
          {messagesToDisplay.map((message) => (
            <article
              key={message.id}
              className={cn("max-w-full", {
                "bg-muted max-w-4/5 self-end rounded-lg px-5 py-2.5":
                  message.role === "user",
              })}
            >
              {message.parts.map((part, i) => {
                switch (part.type) {
                  case "text":
                    return message.role === "assistant" ? (
                      <div
                        key={`${message.id}-${i}`}
                        dangerouslySetInnerHTML={{
                          __html: marked.parse(part.text),
                        }}
                      ></div>
                    ) : (
                      <div key={`${message.id}-${i}`}>{part.text}</div>
                    );
                }
              })}
            </article>
          ))}
          {isLoading && (
            <Icons.Loader className="text-muted-foreground size-5 animate-spin" />
          )}
        </div>
      </ScrollArea>

      {!messagesToDisplay.length && !isLoading && (
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {EXAMPLES.map((example) => (
            <Button
              onClick={() => sendMessage({ text: t(example.prompt) })}
              key={example.prompt}
              variant="outline"
              className="text-muted-foreground h-auto grow flex-col items-start gap-2 py-3 text-left whitespace-normal"
            >
              <example.icon className="size-5 shrink-0" />
              {t(example.prompt)}
            </Button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void sendMessage({ text: input });
          setInput("");
        }}
        className="bg-background sticky bottom-4 w-full md:bottom-6"
      >
        <Textarea
          placeholder={t("ai.placeholder")}
          className="min-h-24 resize-none text-base"
          rows={3}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
        />

        <Button
          className="absolute right-2 bottom-3 size-8 rounded-full"
          size="icon"
          type="submit"
          disabled={isLoading}
          aria-label={t("ai.cta")}
        >
          <Icons.ArrowUp className="size-5" />
        </Button>
      </form>
    </div>
  );
};
