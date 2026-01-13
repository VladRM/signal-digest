"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import { runsApi, settingsApi } from "@/lib/api";
import { loadSettings, normalizeSettings, saveSettings } from "@/lib/settings";
import type { Run, RunStatus } from "@/types";

type RunProgress = {
  phase?: string;
  total?: number;
  completed?: number;
  succeeded?: number;
  failed?: number;
  message?: string;
  current_task?: string;
  updated_at?: string;
  percent?: number;
};

type RunTask = {
  at?: string;
  task?: string;
  stage?: string;
  item_id?: number;
  status?: string;
  detail?: string;
};

function getStatusBadge(status: RunStatus) {
  switch (status) {
    case "success":
      return <Badge variant="default" className="bg-green-500">Success</Badge>;
    case "failed":
      return <Badge variant="destructive">Failed</Badge>;
    case "running":
      return <Badge className="bg-blue-500 text-white">Running</Badge>;
  }
}

function parseRunDate(dateString: string) {
  const hasTimezone = /([zZ]|[+-]\d{2}:\d{2})$/.test(dateString);
  return new Date(hasTimezone ? dateString : `${dateString}Z`);
}

function formatDuration(started: string, finished?: string) {
  const start = parseRunDate(started).getTime();
  const end = finished ? parseRunDate(finished).getTime() : Date.now();
  const duration = Math.max(0, Math.round((end - start) / 1000));

  if (duration < 60) {
    return `${duration}s`;
  }
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;
  return `${minutes}m ${seconds}s`;
}

function formatDateTime(dateString: string) {
  const date = parseRunDate(dateString);
  return date.toLocaleString();
}

function formatRunType(runType: string) {
  const normalized = runType.replace(/_/g, " ");
  if (normalized.toLowerCase() === "ai") {
    return "AI";
  }
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

function getRunProgress(run?: Run | null): RunProgress | null {
  if (!run?.stats_json || typeof run.stats_json !== "object") {
    return null;
  }
  const progress = (run.stats_json as Record<string, unknown>).progress;
  if (!progress || typeof progress !== "object") {
    return null;
  }
  const data = progress as Record<string, unknown>;
  const total = typeof data.total === "number" ? data.total : undefined;
  const completed = typeof data.completed === "number" ? data.completed : undefined;
  const succeeded = typeof data.succeeded === "number" ? data.succeeded : undefined;
  const failed = typeof data.failed === "number" ? data.failed : undefined;
  const phase = typeof data.phase === "string" ? data.phase : undefined;
  const message = typeof data.message === "string" ? data.message : undefined;
  const current_task =
    typeof data.current_task === "string" ? data.current_task : undefined;
  const updated_at = typeof data.updated_at === "string" ? data.updated_at : undefined;
  const percent =
    total !== undefined && completed !== undefined && total > 0
      ? Math.min(100, Math.round((completed / total) * 100))
      : 0;
  return {
    phase,
    total,
    completed,
    succeeded,
    failed,
    message,
    current_task,
    updated_at,
    percent,
  };
}

function getRunTasks(run?: Run | null): RunTask[] {
  if (!run?.stats_json || typeof run.stats_json !== "object") {
    return [];
  }
  const tasks = (run.stats_json as Record<string, unknown>).tasks;
  if (!Array.isArray(tasks)) {
    return [];
  }
  return tasks.filter((task) => typeof task === "object" && task !== null) as RunTask[];
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [runningAI, setRunningAI] = useState(false);
  const [buildingBrief, setBuildingBrief] = useState(false);
  const [expandedRun, setExpandedRun] = useState<number | null>(null);
  const [cancelingRunId, setCancelingRunId] = useState<number | null>(null);
  const aiRunning = runs.some(
    (run) => run.run_type === "ai" && run.status === "running"
  );
  const briefRunning = runs.some(
    (run) => run.run_type === "build_brief" && run.status === "running"
  );
  const hasActiveRequest = triggering || runningAI || buildingBrief;
  const isInitialLoad = loading && runs.length === 0;
  const runningRuns = runs.filter((run) => run.status === "running");
  const currentRun = runningRuns[0];
  const currentProgress = getRunProgress(currentRun);
  const currentTasks = getRunTasks(currentRun);
  const recentTasks = currentTasks.slice(-5).reverse();

  function formatTaskLabel(task: RunTask) {
    if (task.detail) {
      return `${task.task} - ${task.detail}`;
    }
    return task.task ?? "";
  }

  useEffect(() => {
    loadRuns();
  }, []); // Load once on mount

  useEffect(() => {
    const shouldPoll = runningRuns.length > 0 || hasActiveRequest;
    if (!shouldPoll) {
      return;
    }
    const interval = setInterval(() => {
      loadRuns();
    }, 5000);
    return () => clearInterval(interval);
  }, [runningRuns.length, hasActiveRequest]);

  async function resolveSettings() {
    try {
      const remote = await settingsApi.get();
      const normalized = normalizeSettings(remote);
      saveSettings(normalized);
      return normalized;
    } catch {
      return loadSettings();
    }
  }

  async function loadRuns() {
    try {
      setLoading(true);
      const data = await runsApi.list(50);
      setRuns(data);
    } catch (error) {
      toast.error("Failed to load runs");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  async function handleTriggerIngestion() {
    try {
      setTriggering(true);
      toast.info("Starting ingestion...");
      const settings = await resolveSettings();
      const timeRange =
        settings.tavily.time_range === "none"
          ? undefined
          : settings.tavily.time_range;
      const options = {
        rss_max_items: settings.ingestion.rss_max_items,
        youtube_max_items: settings.ingestion.youtube_max_items,
        twitter_max_items: settings.ingestion.twitter_max_items,
        tavily: {
          search_depth: settings.tavily.search_depth,
          max_results: settings.tavily.max_results,
          topic: settings.tavily.topic,
          time_range: timeRange,
          include_raw_content: settings.tavily.include_raw_content,
        },
      };
      await runsApi.triggerIngestion(options);
      toast.success("Ingestion completed!");
      loadRuns();
    } catch (error: any) {
      toast.error(`Ingestion failed: ${error.message || "Unknown error"}`);
      console.error(error);
      loadRuns(); // Refresh to show the failed run
    } finally {
      setTriggering(false);
    }
  }

  async function handleRunAI() {
    try {
      setRunningAI(true);
      toast.info("Starting AI processing...");
      const settings = await resolveSettings();
      const run = await runsApi.triggerAI({
        timeout_seconds: settings.ai.timeout_seconds,
      });
      toast.success("AI processing started.");
      loadRuns();
    } catch (error: any) {
      toast.error(`AI processing failed: ${error.message || "Unknown error"}`);
      console.error(error);
      loadRuns();
    } finally {
      setRunningAI(false);
    }
  }

  async function handleBuildBrief() {
    try {
      setBuildingBrief(true);
      toast.info("Building today's brief...");
      loadRuns();
      const settings = await resolveSettings();
      const run = await runsApi.buildBrief({ options: settings.brief });
      toast.success(`Brief created with ${run.stats_json?.items_selected || 0} items!`);
      loadRuns();
    } catch (error: any) {
      toast.error(`Brief building failed: ${error.message || "Unknown error"}`);
      console.error(error);
      loadRuns();
    } finally {
      setBuildingBrief(false);
    }
  }

  async function handleCancelRun(runId: number) {
    try {
      setCancelingRunId(runId);
      await runsApi.cancel(runId);
      toast.success("Run cancelled.");
      loadRuns();
    } catch (error: any) {
      toast.error(`Failed to cancel run: ${error.message || "Unknown error"}`);
      console.error(error);
      loadRuns();
    } finally {
      setCancelingRunId(null);
    }
  }

  if (loading && runs.length === 0 && !hasActiveRequest) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Runs</h1>
        <p className="text-muted-foreground mt-1">
          Trigger ingestion and view run history
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Manual Triggers</CardTitle>
          <CardDescription>
            Run the full pipeline: ingestion → AI processing → brief building
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={handleTriggerIngestion}
              disabled={triggering}
              size="lg"
            >
              {triggering ? "Running..." : "1. Ingest All Endpoints"}
            </Button>
            <Button
              onClick={handleRunAI}
              disabled={runningAI || aiRunning}
              size="lg"
              variant="outline"
            >
              {runningAI || aiRunning ? "AI Running..." : "2. Run AI Processing"}
            </Button>
            <Button
              onClick={handleBuildBrief}
              disabled={buildingBrief || briefRunning || isInitialLoad}
              size="lg"
              variant="outline"
            >
              {buildingBrief || briefRunning ? "Building..." : "3. Build Today's Brief"}
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">
            Configure defaults in{" "}
            <Link href="/settings" className="text-foreground underline">
              Settings
            </Link>
            .
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Run History</CardTitle>
          <CardDescription>Recent ingestion and processing runs</CardDescription>
        </CardHeader>
        <CardContent>
          {currentRun && (
            <div className="mb-4 rounded-lg border bg-muted/30 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase text-muted-foreground">
                    Current Run
                  </p>
                  <p className="text-base font-semibold">
                    {formatRunType(currentRun.run_type)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Started {formatDateTime(currentRun.started_at)} ·{" "}
                    {formatDuration(currentRun.started_at, currentRun.finished_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {(currentRun.run_type === "ai" ||
                    currentRun.run_type === "build_brief") &&
                    currentRun.status === "running" && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={cancelingRunId === currentRun.id}
                        onClick={() => handleCancelRun(currentRun.id)}
                      >
                        {cancelingRunId === currentRun.id ? "Canceling..." : "Cancel"}
                      </Button>
                    )}
                  {getStatusBadge(currentRun.status)}
                </div>
              </div>
              <div className="mt-3">
                {currentProgress ? (
                  <div className="space-y-2">
                    {currentProgress.current_task && (
                      <div className="text-sm font-medium">
                        {currentProgress.current_task}
                      </div>
                    )}
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>
                        {currentProgress.message ||
                          (currentProgress.phase
                            ? `${currentProgress.phase.replace("_", " ")} running`
                            : "Running")}
                      </span>
                      {currentProgress.total !== undefined &&
                        currentProgress.completed !== undefined && (
                          <span>
                            {currentProgress.completed} / {currentProgress.total}
                            {currentProgress.percent !== undefined
                              ? ` (${currentProgress.percent}%)`
                              : ""}
                          </span>
                        )}
                    </div>
                    <div className="h-2 w-full rounded-full bg-muted">
                      <div
                        className="h-2 rounded-full bg-blue-500 transition-all"
                        style={{ width: `${currentProgress.percent ?? 0}%` }}
                      />
                    </div>
                    {recentTasks.length > 0 && (
                      <div className="rounded-md border bg-background p-2 text-xs text-muted-foreground">
                        <div className="mb-1 font-semibold text-foreground">
                          Recent tasks
                        </div>
                        <div className="space-y-1">
                          {recentTasks.map((task, index) => (
                            <div key={`${task.at ?? "task"}-${index}`}>
                              {formatTaskLabel(task)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Waiting for progress updates...
                  </p>
                )}
                {runningRuns.length > 1 && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {runningRuns.length - 1} more run(s) in progress.
                  </p>
                )}
              </div>
            </div>
          )}
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Stats</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      No runs yet. Click "Ingest All Endpoints" to start.
                    </TableCell>
                  </TableRow>
                ) : (
                  runs.map((run) => {
                    const progress = getRunProgress(run);
                    return (
                    <React.Fragment key={run.id}>
                      <TableRow>
                        <TableCell className="font-medium">
                          {formatRunType(run.run_type)}
                        </TableCell>
                        <TableCell>{getStatusBadge(run.status)}</TableCell>
                        <TableCell className="text-sm">
                          {formatDateTime(run.started_at)}
                        </TableCell>
                        <TableCell>
                          {formatDuration(run.started_at, run.finished_at)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {run.status === "running" ? (
                            "-"
                          ) : run.stats_json ? (
                            <>
                              {run.stats_json.total_new !== undefined && (
                                <span className="text-green-600 font-medium">
                                  {run.stats_json.total_new} new
                                </span>
                              )}
                              {run.stats_json.total_skipped !== undefined && (
                                <span className="text-muted-foreground ml-2">
                                  / {run.stats_json.total_skipped} skipped
                                </span>
                              )}
                              {(run.stats_json.endpoints_processed !== undefined ||
                                run.stats_json.sources_processed !== undefined) && (
                                <span className="text-muted-foreground ml-2">
                                  from{" "}
                                  {run.stats_json.endpoints_processed ??
                                    run.stats_json.sources_processed}{" "}
                                  endpoints
                                </span>
                              )}
                              {run.stats_json.topics_processed !== undefined && (
                                <span className="text-muted-foreground ml-2">
                                  {run.stats_json.topics_processed} topics
                                </span>
                              )}
                              {run.stats_json.total_results !== undefined && (
                                <span className="text-muted-foreground ml-2">
                                  / {run.stats_json.total_results} results
                                </span>
                              )}
                            </>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            {(run.run_type === "ai" ||
                              run.run_type === "build_brief") &&
                              run.status === "running" && (
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={cancelingRunId === run.id}
                                onClick={() => handleCancelRun(run.id)}
                              >
                                {cancelingRunId === run.id ? "Canceling..." : "Cancel"}
                              </Button>
                            )}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                setExpandedRun(
                                  expandedRun === run.id ? null : run.id
                                )
                              }
                            >
                              {expandedRun === run.id ? "Hide" : "Details"}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                      {expandedRun === run.id && (
                        <TableRow>
                          <TableCell colSpan={6} className="bg-muted/50">
                            <div className="p-4 space-y-4">
                              {run.error_text && (
                                <div>
                                  <h4 className="font-semibold text-red-600 mb-2">
                                    Errors:
                                  </h4>
                                  <pre className="text-sm bg-red-50 p-3 rounded whitespace-pre-wrap break-words">
                                    {run.error_text}
                                  </pre>
                                </div>
                              )}
                              {run.stats_json && (
                                <div>
                                  <h4 className="font-semibold mb-2">
                                    Detailed Stats:
                                  </h4>
                                  <pre className="text-sm bg-background p-3 rounded whitespace-pre-wrap break-words">
                                    {JSON.stringify(run.stats_json, null, 2)}
                                  </pre>
                                </div>
                              )}
                              {getRunTasks(run).length > 0 && (
                                <div>
                                  <h4 className="font-semibold mb-2">Task Log:</h4>
                                  <div className="space-y-1 text-sm">
                                    {getRunTasks(run)
                                      .slice(-50)
                                      .map((task, index) => (
                                        <div
                                          key={`${task.at ?? "task"}-${index}`}
                                          className="rounded border bg-background px-2 py-1"
                                        >
                                          <div className="text-xs text-muted-foreground">
                                            {task.at}
                                          </div>
                                          <div>{formatTaskLabel(task)}</div>
                                          {task.detail && (
                                            <div className="text-xs text-muted-foreground">
                                              {task.detail}
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
