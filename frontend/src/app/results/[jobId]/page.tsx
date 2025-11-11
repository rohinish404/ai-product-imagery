"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ApiClient, JobResults } from "@/lib/api";
import { Download, Home, Loader2 } from "lucide-react";

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const [results, setResults] = useState<JobResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId) return;

    const fetchResults = async () => {
      try {
        const data = await ApiClient.getJobResults(jobId);
        setResults(data);
      } catch (err) {
        console.error("Error fetching results:", err);
        setError("Failed to fetch results. The job may not be completed yet.");
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [jobId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!results) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900">
      <div className="container mx-auto px-4 py-8">
        {}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50">
              Processing Results
            </h1>
            <p className="text-zinc-600 dark:text-zinc-400 mt-2">
              Found {results.products.length} product(s)
            </p>
          </div>
          <Button onClick={() => router.push("/")} variant="outline">
            <Home className="mr-2 h-4 w-4" />
            New Video
          </Button>
        </div>

        {}
        <div className="space-y-8">
          {results.products.map((product, idx) => {
            const productName = product.name;
            const bestFrame = results.best_frames[productName];
            const segmentedImage = results.segmented_images[productName];
            const enhancedImages = results.enhanced_images[productName] || [];
            const segmentationError = results.segmentation_errors?.[productName];
            const enhancementError = results.enhancement_errors?.[productName];

            return (
              <Card key={idx}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{product.name}</CardTitle>
                      <CardDescription>{product.description}</CardDescription>
                    </div>
                    <Badge>Product {idx + 1}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="original" className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="original">Original Frame</TabsTrigger>
                      <TabsTrigger value="segmented">Segmented</TabsTrigger>
                      <TabsTrigger value="enhanced">Enhanced</TabsTrigger>
                    </TabsList>

                    {}
                    <TabsContent value="original" className="space-y-4">
                      <div className="relative w-full aspect-video bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden">
                        {bestFrame && (
                          <img
                            src={ApiClient.getImageUrl(jobId, "frames", bestFrame)}
                            alt={`Best frame of ${product.name}`}
                            className="w-full h-full object-contain"
                          />
                        )}
                      </div>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        AI-selected best frame showing the product clearly
                      </p>
                    </TabsContent>

                    {}
                    <TabsContent value="segmented" className="space-y-4">
                      <div className="relative w-full aspect-video bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden">
                        {segmentedImage ? (
                          <img
                            src={ApiClient.getImageUrl(jobId, "segmented", segmentedImage)}
                            alt={`Segmented ${product.name}`}
                            className="w-full h-full object-contain"
                          />
                        ) : (
                          <div className="flex items-center justify-center h-full p-8">
                            <div className="text-center space-y-2">
                              <p className="text-zinc-900 dark:text-zinc-50 font-medium">
                                Segmentation Failed
                              </p>
                              {segmentationError && (
                                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                                  {segmentationError}
                                </p>
                              )}
                              <p className="text-xs text-zinc-500 dark:text-zinc-500 mt-2">
                                This may be due to API rate limits. Try again in a few minutes.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-zinc-600 dark:text-zinc-400">
                          Product isolated with transparent background
                        </p>
                        {segmentedImage && (
                          <Button size="sm" variant="outline" asChild>
                            <a
                              href={ApiClient.getImageUrl(jobId, "segmented", segmentedImage)}
                              download
                            >
                              <Download className="mr-2 h-4 w-4" />
                              Download
                            </a>
                          </Button>
                        )}
                      </div>
                    </TabsContent>

                    {}
                    <TabsContent value="enhanced" className="space-y-4">
                      {enhancedImages.length > 0 ? (
                        <>
                          <div className="grid md:grid-cols-3 gap-4">
                            {enhancedImages.map((image, imgIdx) => (
                              <div key={imgIdx} className="space-y-2">
                                <div className="relative w-full aspect-square bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden">
                                  <img
                                    src={ApiClient.getImageUrl(jobId, "enhanced", image)}
                                    alt={`Enhanced ${product.name} - Style ${imgIdx + 1}`}
                                    className="w-full h-full object-contain"
                                  />
                                </div>
                                <Button size="sm" variant="outline" className="w-full" asChild>
                                  <a
                                    href={ApiClient.getImageUrl(jobId, "enhanced", image)}
                                    download
                                  >
                                    <Download className="mr-2 h-4 w-4" />
                                    Style {imgIdx + 1}
                                  </a>
                                </Button>
                              </div>
                            ))}
                          </div>
                          <p className="text-sm text-zinc-600 dark:text-zinc-400">
                            AI-generated professional product shots with different backgrounds
                          </p>
                          {enhancementError && (
                            <Alert variant="default" className="mt-4">
                              <AlertDescription>
                                <strong>Note:</strong> Some enhancements failed. {enhancementError}
                              </AlertDescription>
                            </Alert>
                          )}
                        </>
                      ) : (
                        <div className="relative w-full aspect-video bg-zinc-100 dark:bg-zinc-800 rounded-lg overflow-hidden">
                          <div className="flex items-center justify-center h-full p-8">
                            <div className="text-center space-y-2">
                              <p className="text-zinc-900 dark:text-zinc-50 font-medium">
                                Enhancement Failed
                              </p>
                              {enhancementError && (
                                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                                  {enhancementError}
                                </p>
                              )}
                              <p className="text-xs text-zinc-500 dark:text-zinc-500 mt-2">
                                This may be due to API rate limits. Try again in a few minutes.
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
