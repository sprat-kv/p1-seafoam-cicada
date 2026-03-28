"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { CaseCard } from "@/components/case-card";
import { CaseDetailModal } from "@/components/case-detail-modal";
import { getCaseHistory } from "@/lib/api";
import { CaseHistoryRow, CaseStatus } from "@/lib/types";
import { RefreshCw, Inbox, Loader2, AlertCircle } from "lucide-react";

export default function CasesPage() {
    const [cases, setCases] = useState<CaseHistoryRow[]>([]);
    const [selectedCase, setSelectedCase] = useState<CaseHistoryRow | null>(null);
    const [statusFilter, setStatusFilter] = useState<CaseStatus | "all">("all");
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchCases = async () => {
        try {
            setIsRefreshing(true);
            setError(null);
            
            // Pass undefined for status if 'all' is selected
            const response = await getCaseHistory({
                status: statusFilter === "all" ? undefined : statusFilter,
                limit: 50,
            });
            
            setCases(response.rows);
        } catch (error) {
            console.error("Error fetching cases:", error);
            setError("Unable to connect to the backend API. Please ensure the backend server is running.");
        } finally {
            setIsLoading(false);
            setIsRefreshing(false);
        }
    };

    // Use effect depends on statusFilter, so fetch on change
    useEffect(() => {
        setIsLoading(true);
        fetchCases();
    }, [statusFilter]);

    const handleCaseClick = (caseRow: CaseHistoryRow) => {
        setSelectedCase(caseRow);
    };

    const handleCloseDetail = () => {
        setSelectedCase(null);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-4xl font-bold tracking-tight mb-2">
                                Case History
                            </h1>
                            <p className="text-muted-foreground">
                                View past customer cases and resolutions
                            </p>
                        </div>
                        <Button
                            onClick={fetchCases}
                            disabled={isRefreshing}
                            variant="outline"
                            size="lg"
                        >
                            {isRefreshing ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <RefreshCw className="h-4 w-4 mr-2" />
                            )}
                            Refresh
                        </Button>
                    </div>
                </div>

                {/* Error State */}
                {error && (
                    <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
                        <div className="flex-1">
                            <h3 className="font-semibold text-destructive mb-1">Connection Error</h3>
                            <p className="text-sm text-destructive/90">{error}</p>
                            <p className="text-sm text-muted-foreground mt-2">
                                Backend API URL: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
                            </p>
                        </div>
                    </div>
                )}

                {/* Filters and Count */}
                {!error && (
                    <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="flex flex-wrap gap-2">
                            <Button 
                                variant={statusFilter === "all" ? "default" : "outline"} 
                                onClick={() => setStatusFilter("all")}
                                size="sm"
                            >
                                All Cases
                            </Button>
                            <Button 
                                variant={statusFilter === "active" ? "default" : "outline"} 
                                onClick={() => setStatusFilter("active")}
                                size="sm"
                            >
                                Active
                            </Button>
                            <Button 
                                variant={statusFilter === "in_review" ? "default" : "outline"} 
                                onClick={() => setStatusFilter("in_review")}
                                size="sm"
                            >
                                In Review
                            </Button>
                            <Button 
                                variant={statusFilter === "closed" ? "default" : "outline"} 
                                onClick={() => setStatusFilter("closed")}
                                size="sm"
                            >
                                Closed
                            </Button>
                        </div>
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full shrink-0">
                            <Inbox className="h-4 w-4 text-primary" />
                            <span className="text-sm font-medium">
                                {cases.length} {cases.length === 1 ? "Case" : "Cases"} Found
                            </span>
                        </div>
                    </div>
                )}

                {/* Loading State */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    <>
                        {/* Empty State */}
                        {cases.length === 0 && !error ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed rounded-lg bg-muted/10">
                                <div className="bg-muted/50 rounded-full p-6 mb-4">
                                    <Inbox className="h-12 w-12 text-muted-foreground" />
                                </div>
                                <h3 className="text-xl font-semibold mb-2">No Cases Found</h3>
                                <p className="text-muted-foreground max-w-md">
                                    {statusFilter === "all" 
                                        ? "There are no cases in the system yet." 
                                        : `There are no cases with the status '${statusFilter.replace("_", " ")}'.`}
                                </p>
                            </div>
                        ) : !error ? (
                            /* Cases Grid */
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {cases.map((caseRow) => (
                                    <CaseCard
                                        key={caseRow.case_id}
                                        caseRow={caseRow}
                                        onClick={() => handleCaseClick(caseRow)}
                                    />
                                ))}
                            </div>
                        ) : null}
                    </>
                )}
            </div>

            {/* Case Detail Modal */}
            <CaseDetailModal
                caseRow={selectedCase}
                isOpen={!!selectedCase}
                onClose={handleCloseDetail}
            />
        </div>
    );
}
