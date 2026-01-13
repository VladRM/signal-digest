"use client";

import { useState, useEffect } from "react";
import { TopicBriefSection } from "@/components/topic-brief-section";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { briefsApi } from "@/lib/api";
import { Calendar } from "lucide-react";

interface TopicBrief {
  id: number;
  topic_id: number;
  topic_name: string;
  summary_short: string;
  summary_full: string;
  content_references: Array<{
    content_item_id: number;
    title: string;
    url: string;
    key_point: string;
  }>;
  key_themes: string[];
  significance: string;
}

export default function BriefPage() {
  const [brief, setBrief] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());

  useEffect(() => {
    loadBrief(selectedDate);
  }, [selectedDate]);

  async function loadBrief(date: Date) {
    try {
      setLoading(true);
      const dateStr = date.toISOString().split("T")[0];
      const data = await briefsApi.get(dateStr);
      setBrief(data);
    } catch (error: any) {
      if (error.status === 404) {
        setBrief(null);
      } else {
        toast.error("Failed to load brief");
        console.error(error);
      }
    } finally {
      setLoading(false);
    }
  }

  function handleDateChange(offset: number) {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + offset);
    setSelectedDate(newDate);
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Morning Brief</h1>
          <p className="text-muted-foreground mt-1">
            {selectedDate.toLocaleDateString("en-US", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDateChange(-1)}
          >
            ← Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedDate(new Date())}
          >
            <Calendar className="w-4 h-4 mr-2" />
            Today
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDateChange(1)}
            disabled={
              selectedDate.toDateString() === new Date().toDateString()
            }
          >
            Next →
          </Button>
        </div>
      </div>

      {!brief ? (
        <div className="text-center py-12 bg-muted/50 rounded-lg">
          <p className="text-muted-foreground text-lg mb-2">
            No brief available for this date.
          </p>
          <p className="text-sm text-muted-foreground">
            Run ingestion, AI processing, and build brief to see content here.
          </p>
        </div>
      ) : (
        <div>
          {brief.topic_briefs && brief.topic_briefs.length > 0 ? (
            <>
              <p className="text-sm text-muted-foreground mb-4">
                {brief.topic_briefs.length} topic{brief.topic_briefs.length !== 1 ? 's' : ''} briefed
              </p>

              {brief.topic_briefs.map((topicBrief: TopicBrief) => (
                <TopicBriefSection
                  key={topicBrief.id}
                  topicName={topicBrief.topic_name}
                  summaryShort={topicBrief.summary_short}
                  summaryFull={topicBrief.summary_full}
                  contentReferences={topicBrief.content_references}
                  keyThemes={topicBrief.key_themes}
                  significance={topicBrief.significance}
                />
              ))}
            </>
          ) : (
            <div className="text-center py-12 bg-muted/50 rounded-lg">
              <p className="text-muted-foreground text-lg mb-2">
                No AI topic briefs available yet.
              </p>
              <p className="text-sm text-muted-foreground">
                Topic briefs are automatically generated when you build a brief.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
