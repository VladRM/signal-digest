"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { exploreApi, topicsApi } from "@/lib/api";
import type { Topic } from "@/types";
import { ExternalLink } from "lucide-react";

export default function ExplorePage() {
  const [items, setItems] = useState<any[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTopics();
  }, []);

  useEffect(() => {
    loadItems();
  }, [selectedTopic]);

  async function loadTopics() {
    try {
      const data = await topicsApi.list();
      setTopics(data);
    } catch (error) {
      toast.error("Failed to load topics");
      console.error(error);
    }
  }

  async function loadItems() {
    try {
      setLoading(true);
      const filters: any = {};
      if (selectedTopic && selectedTopic !== "all") {
        filters.topic_id = parseInt(selectedTopic);
      }
      const data = await exploreApi.list(filters);
      setItems(data);
    } catch (error) {
      toast.error("Failed to load content");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Explore Content</h1>

      {/* Filters */}
      <div className="mb-6 flex gap-4">
        <Select value={selectedTopic} onValueChange={setSelectedTopic}>
          <SelectTrigger className="w-[280px]">
            <SelectValue placeholder="Filter by topic" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All topics</SelectItem>
            {topics.map((topic) => (
              <SelectItem key={topic.id} value={topic.id.toString()}>
                {topic.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selectedTopic && selectedTopic !== "all" && (
          <Button variant="outline" onClick={() => setSelectedTopic("all")}>
            Clear filter
          </Button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-muted/50 rounded-lg">
          <p className="text-muted-foreground">No content found.</p>
          <p className="text-sm text-muted-foreground mt-2">
            Run ingestion and AI processing to see content here.
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground mb-4">
            {items.length} items found
          </p>

          <div className="space-y-4">
            {items.map((item) => (
              <Card key={item.id}>
                <CardHeader>
                  <CardTitle className="text-lg">{item.title}</CardTitle>
                  {item.author && (
                    <p className="text-sm text-muted-foreground">
                      by {item.author}
                    </p>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Summary */}
                  {item.extraction.summary_bullets && (
                    <div>
                      <h4 className="font-semibold text-sm mb-2">Summary</h4>
                      <ul className="list-disc list-inside space-y-1">
                        {item.extraction.summary_bullets.map(
                          (bullet: string, i: number) => (
                            <li key={i} className="text-sm">
                              {bullet}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {item.raw_text && (
                    <details className="rounded border bg-muted/30 p-3">
                      <summary className="cursor-pointer text-sm font-semibold">
                        Content (markdown)
                      </summary>
                      <pre className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">
                        {item.raw_text}
                      </pre>
                    </details>
                  )}

                  {/* Topics */}
                  <div className="flex flex-wrap gap-2">
                    {item.topics.map((topic: any, i: number) => (
                      <Badge key={i} variant="secondary">
                        {topic.topic_name}
                      </Badge>
                    ))}
                  </div>

                  {/* Metadata */}
                  <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                    {item.endpoint ? (
                      <span>
                        Endpoint: {item.endpoint.name} ({item.endpoint.connector_type})
                      </span>
                    ) : item.connector_query ? (
                      <span>
                        Connector: {item.connector_type} · Query:{" "}
                        {item.connector_query.query}
                      </span>
                    ) : (
                      <span>Connector: {item.connector_type}</span>
                    )}
                    {item.published_at && (
                      <span>
                        Published:{" "}
                        {new Date(item.published_at).toLocaleDateString()}
                      </span>
                    )}
                    {item.extraction.confidence_overall && (
                      <Badge
                        variant="outline"
                        className={
                          item.extraction.confidence_overall === "high"
                            ? "bg-green-100 text-green-800"
                            : item.extraction.confidence_overall === "med"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-gray-100 text-gray-800"
                        }
                      >
                        {item.extraction.confidence_overall} confidence
                      </Badge>
                    )}
                  </div>

                  {/* Item link */}
                  <div className="pt-2 border-t">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Open item
                    </a>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
