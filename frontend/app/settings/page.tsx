"use client";

import React, { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { settingsApi } from "@/lib/api";
import { DEFAULT_SETTINGS, loadSettings, normalizeSettings, saveSettings } from "@/lib/settings";
import type { AppSettings } from "@/types";

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">(
    "idle"
  );
  const skipSaveRef = useRef(true);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadRemote = async () => {
      try {
        const remote = await settingsApi.get();
        if (!isMounted) return;
        const normalized = normalizeSettings(remote);
        skipSaveRef.current = true;
        setSettings(normalized);
        saveSettings(normalized);
      } catch {
        if (!isMounted) return;
        skipSaveRef.current = true;
        setSettings(loadSettings());
      }
    };
    loadRemote();
    return () => {
      isMounted = false;
    };
  }, []);

  const updateSettings = (updater: (current: AppSettings) => AppSettings) => {
    setSettings((current) => updater(current));
  };

  const updateNumber =
    (updater: (current: AppSettings, value: number) => AppSettings) =>
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const raw = event.target.value;
      const value = Number.parseInt(raw, 10);
      if (!Number.isFinite(value)) {
        return;
      }
      updateSettings((current) => updater(current, value));
    };

  useEffect(() => {
    if (skipSaveRef.current) {
      skipSaveRef.current = false;
      return;
    }
    saveSettings(settings);
    setSaveState("saving");
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await settingsApi.update(settings);
        setSaveState("saved");
      } catch {
        setSaveState("error");
      }
    }, 400);
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [settings]);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Saved automatically for future runs.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          {saveState === "saving" && "Saving..."}
          {saveState === "saved" && "Saved"}
          {saveState === "error" && "Save failed"}
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Ingestion Limits</CardTitle>
            <CardDescription>Per-endpoint caps for ingestion runs.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>RSS max items</Label>
              <Input
                type="number"
                min={0}
                value={settings.ingestion.rss_max_items}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  ingestion: { ...current.ingestion, rss_max_items: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>YouTube max items</Label>
              <Input
                type="number"
                min={0}
                value={settings.ingestion.youtube_max_items}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  ingestion: { ...current.ingestion, youtube_max_items: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>X/Twitter max items</Label>
              <Input
                type="number"
                min={0}
                value={settings.ingestion.twitter_max_items}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  ingestion: { ...current.ingestion, twitter_max_items: value },
                }))}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tavily Settings</CardTitle>
            <CardDescription>Search defaults for Tavily ingestion.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Search depth</Label>
              <Select
                value={settings.tavily.search_depth}
                onValueChange={(value) =>
                  updateSettings((current) => ({
                    ...current,
                    tavily: {
                      ...current.tavily,
                      search_depth: value as AppSettings["tavily"]["search_depth"],
                    },
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="basic">basic</SelectItem>
                  <SelectItem value="advanced">advanced</SelectItem>
                  <SelectItem value="fast">fast</SelectItem>
                  <SelectItem value="ultra-fast">ultra-fast</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Max results</Label>
              <Input
                type="number"
                min={0}
                max={20}
                value={settings.tavily.max_results}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  tavily: { ...current.tavily, max_results: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Topic</Label>
              <Select
                value={settings.tavily.topic}
                onValueChange={(value) =>
                  updateSettings((current) => ({
                    ...current,
                    tavily: {
                      ...current.tavily,
                      topic: value as AppSettings["tavily"]["topic"],
                    },
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">general</SelectItem>
                  <SelectItem value="news">news</SelectItem>
                  <SelectItem value="finance">finance</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Time range</Label>
              <Select
                value={settings.tavily.time_range}
                onValueChange={(value) =>
                  updateSettings((current) => ({
                    ...current,
                    tavily: {
                      ...current.tavily,
                      time_range: value as AppSettings["tavily"]["time_range"],
                    },
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">none</SelectItem>
                  <SelectItem value="day">day</SelectItem>
                  <SelectItem value="week">week</SelectItem>
                  <SelectItem value="month">month</SelectItem>
                  <SelectItem value="year">year</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Raw markdown</Label>
              <Select
                value={settings.tavily.include_raw_content ? "true" : "false"}
                onValueChange={(value) =>
                  updateSettings((current) => ({
                    ...current,
                    tavily: {
                      ...current.tavily,
                      include_raw_content: value === "true",
                    },
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="true">include</SelectItem>
                  <SelectItem value="false">exclude</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>AI Processing</CardTitle>
            <CardDescription>Controls AI run limits.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>AI run timeout (seconds)</Label>
              <Input
                type="number"
                min={60}
                value={settings.ai.timeout_seconds}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  ai: { ...current.ai, timeout_seconds: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Classification timeout (seconds)</Label>
              <Input
                type="number"
                min={10}
                value={settings.ai.classification_timeout_seconds}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  ai: { ...current.ai, classification_timeout_seconds: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Extraction timeout (seconds)</Label>
              <Input
                type="number"
                min={10}
                value={settings.ai.extraction_timeout_seconds}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  ai: { ...current.ai, extraction_timeout_seconds: value },
                }))}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Brief Builder</CardTitle>
            <CardDescription>Selection caps for daily briefs.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>Max items</Label>
              <Input
                type="number"
                min={0}
                value={settings.brief.max_items}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  brief: { ...current.brief, max_items: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Max per topic</Label>
              <Input
                type="number"
                min={0}
                value={settings.brief.max_per_topic}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  brief: { ...current.brief, max_per_topic: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Lookback hours</Label>
              <Input
                type="number"
                min={1}
                value={settings.brief.lookback_hours}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  brief: { ...current.brief, lookback_hours: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Topic brief timeout (seconds)</Label>
              <Input
                type="number"
                min={30}
                value={settings.brief.topic_brief_timeout_seconds}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  brief: { ...current.brief, topic_brief_timeout_seconds: value },
                }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Topic brief batch size</Label>
              <Input
                type="number"
                min={5}
                max={50}
                value={settings.brief.topic_brief_batch_size}
                onChange={updateNumber((current, value) => ({
                  ...current,
                  brief: { ...current.brief, topic_brief_batch_size: value },
                }))}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
