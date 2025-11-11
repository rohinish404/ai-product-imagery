"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ApiClient, JobStatus } from "@/lib/api";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

export default function ProcessPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId) return;

    let intervalId: NodeJS.Timeout;

    const checkStatus = async () => {
      try {
        const jobStatus = await ApiClient.getJobStatus(jobId);
        setStatus(jobStatus);

                if (jobStatus.status === "completed") {
          clearInterval(intervalId);
          setTimeout(() => {
            router.push(`/results/${jobId}`);
          }, 2000);
        }

                if (jobStatus.status === "error") {
          clearInterval(intervalId);
          setError(jobStatus.error || "An error occurred during processing");
        }
      } catch (err) {
        console.error("Error checking status:", err);
        setError("Failed to fetch job status");
        clearInterval(intervalId);
      }
    };

        checkStatus();

        intervalId = setInterval(checkStatus, 2000);

    return () => {
      clearInterval(intervalId);
    };
  }, [jobId, router]);

  const getStatusIcon = () => {
    if (status?.status === "completed") {
      return <CheckCircle2 className="h-8 w-8 text-green-500" />;
    }
    if (status?.status === "error") {
      return <XCircle className="h-8 w-8 text-red-500" />;
    }
    return <Loader2 className="h-8 w-8 animate-spin text-blue-500" />;
  };

  const getStatusBadge = () => {
    if (!status) return null;

    const variants: Record<string, "default" | "secondary" | "destructive"> = {
      processing: "default",
      completed: "secondary",
      error: "destructive",
    };

    return (
      <Badge variant={variants[status.status] || "default"}>
        {status.status}
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Processing Video</CardTitle>
                  <CardDescription>
                    Job ID: <span className="font-mono text-xs">{jobId}</span>
                  </CardDescription>
                </div>
                {getStatusBadge()}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {}
              <div className="flex flex-col items-center justify-center py-8 space-y-4">
                {getStatusIcon()}
                <p className="text-lg font-medium text-center">
                  {status?.current_step || "Initializing..."}
                </p>
              </div>

              {}
              {status && status.status === "processing" && (
                <div className="space-y-2">
                  <Progress value={status.progress} className="w-full" />
                  <p className="text-sm text-center text-zinc-600 dark:text-zinc-400">
                    {status.progress}% complete
                  </p>
                </div>
              )}

              {}
              {error && (
                <Alert variant="destructive">
                  <XCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {}
              {status?.status === "completed" && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <AlertDescription>
                    Processing complete! Redirecting to results...
                  </AlertDescription>
                </Alert>
              )}

              {}
              <div className="space-y-2">
                <p className="text-sm font-medium">Processing Pipeline:</p>
                <ol className="text-sm space-y-1 list-decimal list-inside text-zinc-600 dark:text-zinc-400">
                  <li>Download video from YouTube</li>
                  <li>Extract frames from video</li>
                  <li>Identify products using AI</li>
                  <li>Segment products from frames</li>
                  <li>Enhance product images</li>
                </ol>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
