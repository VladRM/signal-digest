/**
 * Brief card component for displaying content items in the daily brief
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Search, Youtube, Twitter } from "lucide-react";

interface BriefCardProps {
  rank: number;
  title: string;
  summary: string[];
  whyItMatters: string[];
  topics: Array<{ topic_name: string; score: number }>;
  confidence: "low" | "med" | "high";
  connectorType: string;
  url: string;
  author?: string;
  publishedAt?: string;
}

const confidenceColors = {
  high: "bg-green-100 text-green-800 border-green-300",
  med: "bg-yellow-100 text-yellow-800 border-yellow-300",
  low: "bg-gray-100 text-gray-800 border-gray-300",
};

const connectorIcons = {
  rss: ExternalLink,
  youtube_channel: Youtube,
  x_user: Twitter,
  tavily: Search,
};

export function BriefCard({
  rank,
  title,
  summary,
  whyItMatters,
  topics,
  confidence,
  connectorType,
  url,
  author,
  publishedAt,
}: BriefCardProps) {
  const SourceIcon =
    connectorIcons[connectorType as keyof typeof connectorIcons] || ExternalLink;

  return (
    <Card className="mb-4 hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-bold text-muted-foreground">
                #{rank}
              </span>
              <Badge
                variant="outline"
                className={confidenceColors[confidence]}
              >
                {confidence} confidence
              </Badge>
            </div>
            <CardTitle className="text-xl">{title}</CardTitle>
            {author && (
              <p className="text-sm text-muted-foreground mt-1">by {author}</p>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Summary */}
        <div>
          <h4 className="font-semibold mb-2">Summary</h4>
          <ul className="list-disc list-inside space-y-1">
            {summary.map((bullet, i) => (
              <li key={i} className="text-sm">
                {bullet}
              </li>
            ))}
          </ul>
        </div>

        {/* Why it matters */}
        <div>
          <h4 className="font-semibold mb-2">Why it matters</h4>
          <ul className="list-disc list-inside space-y-1">
            {whyItMatters.map((reason, i) => (
              <li key={i} className="text-sm text-muted-foreground">
                {reason}
              </li>
            ))}
          </ul>
        </div>

        {/* Topics */}
        <div className="flex flex-wrap gap-2">
          {topics.map((topic, i) => (
            <Badge key={i} variant="secondary">
              {topic.topic_name}
            </Badge>
          ))}
        </div>

        {/* Item link */}
        <div className="pt-2 border-t">
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline"
          >
            <SourceIcon className="w-4 h-4" />
            Open item
          </a>
        </div>
      </CardContent>
    </Card>
  );
}
