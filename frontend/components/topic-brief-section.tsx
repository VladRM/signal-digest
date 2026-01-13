"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

interface ContentReference {
  content_item_id: number;
  title: string;
  url: string;
  key_point: string;
}

interface TopicBriefSectionProps {
  topicName: string;
  summaryShort: string;
  summaryFull: string;
  contentReferences: ContentReference[];
  keyThemes: string[];
  significance: string;
}

export function TopicBriefSection({
  topicName,
  summaryShort,
  summaryFull,
  contentReferences,
  keyThemes,
  significance,
}: TopicBriefSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const sanitizeSchema = {
    ...defaultSchema,
    attributes: {
      ...defaultSchema.attributes,
      a: [
        ...(defaultSchema.attributes?.a || []),
        "target",
        "rel",
      ],
    },
  };
  const markdownClasses = "prose prose-sm max-w-none text-foreground/90";
  const sectionHeadingClasses = "text-sm font-semibold text-foreground mb-3";
  const summaryHeadingClasses =
    "text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2";

  return (
    <Card className="mb-6 py-0">
      <CardHeader className="py-6">
        <div className="relative">
          <div className="pr-10 space-y-2">
            <h3 className="text-xl font-semibold tracking-tight">
              {topicName}
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {summaryShort}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            aria-label={isExpanded ? "Collapse topic brief" : "Expand topic brief"}
            onClick={() => setIsExpanded(!isExpanded)}
            className="absolute right-0 top-0"
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-6 pb-6">
          {/* Full executive summary */}
          <div>
            <h4 className={summaryHeadingClasses}>Executive Summary</h4>
            <div className="rounded-lg border border-muted/60 bg-muted/20 p-5">
              <div className={markdownClasses}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}
                  components={{
                    h1: (props) => (
                      <h1
                        className="text-lg sm:text-xl font-semibold mt-0 mb-3 pb-2 border-b border-muted/60"
                        {...props}
                      />
                    ),
                    h2: (props) => (
                      <h2
                        className="text-base sm:text-lg font-semibold mt-8 mb-4"
                        {...props}
                      />
                    ),
                    h3: (props) => (
                      <h3
                        className="text-sm sm:text-base font-medium mt-4 mb-2"
                        {...props}
                      />
                    ),
                    p: (props) => (
                      <p
                        className="text-xs sm:text-sm leading-relaxed my-2 text-foreground/90"
                        {...props}
                      />
                    ),
                    ul: (props) => (
                      <ul
                        className="text-xs sm:text-sm my-2 pl-5"
                        {...props}
                      />
                    ),
                    ol: (props) => (
                      <ol
                        className="text-xs sm:text-sm my-2 pl-5"
                        {...props}
                      />
                    ),
                    li: (props) => (
                      <li
                        className="leading-relaxed my-1 text-foreground/90"
                        {...props}
                      />
                    ),
                    strong: (props) => (
                      <strong
                        className="font-semibold text-foreground"
                        {...props}
                      />
                    ),
                    a: (props) => (
                      <a
                        className="text-blue-600 hover:underline"
                        {...props}
                        target="_blank"
                        rel="noopener noreferrer"
                      />
                    ),
                  }}
                >
                  {summaryFull || ""}
                </ReactMarkdown>
              </div>
            </div>
          </div>

          {/* Key themes */}
          {keyThemes && keyThemes.length > 0 && (
            <div>
              <h4 className={sectionHeadingClasses}>Key Themes</h4>
              <div className="flex flex-wrap gap-2">
                {keyThemes.map((theme, i) => (
                  <Badge key={i} variant="secondary">
                    {theme}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Significance */}
          {significance && (
            <div>
              <h4 className={sectionHeadingClasses}>Why It Matters</h4>
              <p className="text-sm text-muted-foreground">{significance}</p>
            </div>
          )}

          {/* Content references */}
          <div>
            <h4 className={sectionHeadingClasses}>
              References ({contentReferences.length})
            </h4>
            <ul className="space-y-2">
              {contentReferences.map((ref, idx) => (
                <li key={ref.content_item_id} className="text-sm">
                  <span className="text-muted-foreground font-medium">[{idx + 1}]</span>{" "}
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline font-medium"
                  >
                    {ref.title}
                  </a>
                  <p className="text-muted-foreground ml-4 mt-1">
                    → {ref.key_point}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
