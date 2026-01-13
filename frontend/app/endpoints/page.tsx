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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { endpointsApi } from "@/lib/api";
import type {
  Endpoint,
  EndpointConnectorType,
  EndpointCreate,
} from "@/types";

export default function EndpointsPage() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<EndpointConnectorType>("rss");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEndpoint, setEditingEndpoint] = useState<Endpoint | null>(null);
  const [formData, setFormData] = useState<EndpointCreate>({
    connector_type: "rss",
    name: "",
    target: "",
    enabled: true,
    weight: 1,
    notes: "",
  });

  useEffect(() => {
    loadEndpoints();
  }, []);

  async function loadEndpoints() {
    try {
      setLoading(true);
      const data = await endpointsApi.list();
      setEndpoints(data);
    } catch (error) {
      toast.error("Failed to load endpoints");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  function openCreateDialog(connectorType: EndpointConnectorType) {
    setEditingEndpoint(null);
    setFormData({
      connector_type: connectorType,
      name: "",
      target: "",
      enabled: true,
      weight: 1,
      notes: "",
    });
    setDialogOpen(true);
  }

  function openEditDialog(endpoint: Endpoint) {
    setEditingEndpoint(endpoint);
    setFormData({
      connector_type: endpoint.connector_type,
      name: endpoint.name,
      target: endpoint.target,
      enabled: endpoint.enabled,
      weight: endpoint.weight,
      notes: endpoint.notes || "",
    });
    setDialogOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editingEndpoint) {
        await endpointsApi.update(editingEndpoint.id, formData);
        toast.success("Endpoint updated successfully");
      } else {
        await endpointsApi.create(formData);
        toast.success("Endpoint created successfully");
      }
      setDialogOpen(false);
      loadEndpoints();
    } catch (error) {
      toast.error(
        editingEndpoint
          ? "Failed to update endpoint"
          : "Failed to create endpoint"
      );
      console.error(error);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure you want to delete this endpoint?")) return;

    try {
      await endpointsApi.delete(id);
      toast.success("Endpoint deleted successfully");
      loadEndpoints();
    } catch (error) {
      toast.error("Failed to delete endpoint");
      console.error(error);
    }
  }

  function getTargetLabel(connectorType: EndpointConnectorType): string {
    switch (connectorType) {
      case "rss":
        return "RSS Feed URL";
      case "youtube_channel":
        return "YouTube Channel ID or URL";
      case "x_user":
        return "X/Twitter Handle";
    }
  }

  function getTargetPlaceholder(connectorType: EndpointConnectorType): string {
    switch (connectorType) {
      case "rss":
        return "https://example.com/feed.xml";
      case "youtube_channel":
        return "UC... or https://youtube.com/@username";
      case "x_user":
        return "@username";
    }
  }

  const filteredEndpoints = endpoints.filter(
    (endpoint) => endpoint.connector_type === activeTab
  );

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Endpoints</h1>
        <p className="text-muted-foreground mt-1">
          Manage connector endpoints: RSS feeds, YouTube channels, and X accounts
        </p>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as EndpointConnectorType)}
      >
        <TabsList>
          <TabsTrigger value="rss">RSS Feeds</TabsTrigger>
          <TabsTrigger value="youtube_channel">YouTube</TabsTrigger>
          <TabsTrigger value="x_user">X/Twitter</TabsTrigger>
        </TabsList>

        <TabsContent value="rss" className="mt-6">
          <EndpointTable
            endpoints={filteredEndpoints}
            onEdit={openEditDialog}
            onDelete={handleDelete}
            onCreate={() => openCreateDialog("rss")}
          />
        </TabsContent>

        <TabsContent value="youtube_channel" className="mt-6">
          <EndpointTable
            endpoints={filteredEndpoints}
            onEdit={openEditDialog}
            onDelete={handleDelete}
            onCreate={() => openCreateDialog("youtube_channel")}
          />
        </TabsContent>

        <TabsContent value="x_user" className="mt-6">
          <EndpointTable
            endpoints={filteredEndpoints}
            onEdit={openEditDialog}
            onDelete={handleDelete}
            onCreate={() => openCreateDialog("x_user")}
          />
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>
                {editingEndpoint ? "Edit Endpoint" : "Create Endpoint"}
              </DialogTitle>
              <DialogDescription>
                {editingEndpoint
                  ? "Update the endpoint details below."
                  : "Add a new connector endpoint."}
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
                <Label htmlFor="target">{getTargetLabel(formData.connector_type)} *</Label>
                <Input
                  id="target"
                  value={formData.target}
                  onChange={(e) =>
                    setFormData({ ...formData, target: e.target.value })
                  }
                  placeholder={getTargetPlaceholder(formData.connector_type)}
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="notes">Notes</Label>
                <Input
                  id="notes"
                  value={formData.notes}
                  onChange={(e) =>
                    setFormData({ ...formData, notes: e.target.value })
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="weight">Weight</Label>
                  <Input
                    id="weight"
                    type="number"
                    min="1"
                    value={formData.weight}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        weight: parseInt(e.target.value) || 1,
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
                {editingEndpoint ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface EndpointTableProps {
  endpoints: Endpoint[];
  onEdit: (endpoint: Endpoint) => void;
  onDelete: (id: number) => void;
  onCreate: () => void;
}

function EndpointTable({
  endpoints,
  onEdit,
  onDelete,
  onCreate,
}: EndpointTableProps) {
  return (
    <div>
      <div className="flex justify-end mb-4">
        <Button onClick={onCreate}>Add Endpoint</Button>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Weight</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {endpoints.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No endpoints yet. Add one to get started.
                </TableCell>
              </TableRow>
            ) : (
              endpoints.map((endpoint) => (
                <TableRow key={endpoint.id}>
                  <TableCell className="font-medium">{endpoint.name}</TableCell>
                  <TableCell className="max-w-md truncate font-mono text-sm">
                    {endpoint.target}
                  </TableCell>
                  <TableCell>{endpoint.weight}</TableCell>
                  <TableCell>
                    <Badge variant={endpoint.enabled ? "default" : "secondary"}>
                      {endpoint.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onEdit(endpoint)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => onDelete(endpoint.id)}
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
    </div>
  );
}
