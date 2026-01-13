"use client";

import { useState, useEffect } from "react";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { topicsApi } from "@/lib/api";
import type { Topic, TopicCreate } from "@/types";

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTopic, setEditingTopic] = useState<Topic | null>(null);
  const [formData, setFormData] = useState<TopicCreate>({
    name: "",
    description: "",
    include_rules: "",
    exclude_rules: "",
    priority: 0,
    enabled: true,
  });

  useEffect(() => {
    loadTopics();
  }, []);

  async function loadTopics() {
    try {
      setLoading(true);
      const data = await topicsApi.list();
      setTopics(data);
    } catch (error) {
      toast.error("Failed to load topics");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  function openCreateDialog() {
    setEditingTopic(null);
    setFormData({
      name: "",
      description: "",
      include_rules: "",
      exclude_rules: "",
      priority: 0,
      enabled: true,
    });
    setDialogOpen(true);
  }

  function openEditDialog(topic: Topic) {
    setEditingTopic(topic);
    setFormData({
      name: topic.name,
      description: topic.description || "",
      include_rules: topic.include_rules || "",
      exclude_rules: topic.exclude_rules || "",
      priority: topic.priority,
      enabled: topic.enabled,
    });
    setDialogOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editingTopic) {
        await topicsApi.update(editingTopic.id, formData);
        toast.success("Topic updated successfully");
      } else {
        await topicsApi.create(formData);
        toast.success("Topic created successfully");
      }
      setDialogOpen(false);
      loadTopics();
    } catch (error) {
      toast.error(editingTopic ? "Failed to update topic" : "Failed to create topic");
      console.error(error);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure you want to delete this topic?")) return;

    try {
      await topicsApi.delete(id);
      toast.success("Topic deleted successfully");
      loadTopics();
    } catch (error) {
      toast.error("Failed to delete topic");
      console.error(error);
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Topics</h1>
          <p className="text-muted-foreground mt-1">
            Manage topics for content classification
          </p>
        </div>
        <Button onClick={openCreateDialog}>Create Topic</Button>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {topics.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No topics yet. Create one to get started.
                </TableCell>
              </TableRow>
            ) : (
              topics.map((topic) => (
                <TableRow key={topic.id}>
                  <TableCell className="font-medium">{topic.name}</TableCell>
                  <TableCell className="max-w-md truncate">
                    {topic.description || "-"}
                  </TableCell>
                  <TableCell>{topic.priority}</TableCell>
                  <TableCell>
                    <Badge variant={topic.enabled ? "default" : "secondary"}>
                      {topic.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(topic)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(topic.id)}
                    >
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>
                {editingTopic ? "Edit Topic" : "Create Topic"}
              </DialogTitle>
              <DialogDescription>
                {editingTopic
                  ? "Update the topic details below."
                  : "Add a new topic for content classification."}
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="description">Description</Label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  rows={4}
                  className="min-h-24 w-full resize-y rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] dark:bg-input/30 md:text-sm"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="include_rules">Include Rules</Label>
                <Input
                  id="include_rules"
                  value={formData.include_rules}
                  onChange={(e) =>
                    setFormData({ ...formData, include_rules: e.target.value })
                  }
                  placeholder="Keywords or rules to include content"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="exclude_rules">Exclude Rules</Label>
                <Input
                  id="exclude_rules"
                  value={formData.exclude_rules}
                  onChange={(e) =>
                    setFormData({ ...formData, exclude_rules: e.target.value })
                  }
                  placeholder="Keywords or rules to exclude content"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="priority">Priority</Label>
                  <Input
                    id="priority"
                    type="number"
                    value={formData.priority}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        priority: parseInt(e.target.value) || 0,
                      })
                    }
                  />
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="enabled">Status</Label>
                  <select
                    id="enabled"
                    value={formData.enabled ? "true" : "false"}
                    onChange={(e) =>
                      setFormData({ ...formData, enabled: e.target.value === "true" })
                    }
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="true">Enabled</option>
                    <option value="false">Disabled</option>
                  </select>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">
                {editingTopic ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
