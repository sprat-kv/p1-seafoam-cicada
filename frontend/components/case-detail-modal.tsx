"use client";

import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CaseHistoryRow } from "@/lib/types";
import { Package, User, Hash, Clock, History } from "lucide-react";

interface CaseDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    caseRow: CaseHistoryRow | null;
}

function getStatusColor(status: string | null) {
    if (status === "closed") return "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800";
    if (status === "in_review") return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800";
    return "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800";
}

function getFinalActionColor(action: string | null) {
    if (!action) return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800";
    if (action.includes("approved")) return "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800";
    if (action.includes("rejected")) return "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800";
    return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800";
}

export function CaseDetailModal({
    isOpen,
    onClose,
    caseRow,
}: CaseDetailModalProps) {
    if (!caseRow) return null;

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle className="text-2xl flex items-center justify-between">
                        <span>Case Details</span>
                        {caseRow.status && (
                            <Badge variant="outline" className={`text-sm ml-4 ${getStatusColor(caseRow.status as any)}`}>
                                {(caseRow.status as string).replace(/_/g, " ").toUpperCase()}
                            </Badge>
                        )}
                    </DialogTitle>
                </DialogHeader>

                <div className="flex-1 min-h-0 overflow-y-auto space-y-6 py-4 pr-2">
                    {/* Identification Details */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                            Information
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="flex items-center gap-2">
                                <Hash className="h-4 w-4 text-muted-foreground" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Case ID</p>
                                    <p className="font-medium">{caseRow.case_id}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <Package className="h-4 w-4 text-muted-foreground" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Order ID</p>
                                    <p className="font-medium">{caseRow.order_id || "N/A"}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-muted-foreground" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Customer</p>
                                    <p className="font-medium">
                                        {caseRow.customer_name || "Unknown"}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <Separator />

                    {/* Actions and Decisions */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                            Resolution
                        </h3>
                        
                        {caseRow.decision_maker_action && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">Decision Maker Action</p>
                                <div className="p-3 bg-muted rounded-lg border border-muted-foreground/10">
                                    <p className="text-sm whitespace-pre-wrap">
                                        {caseRow.decision_maker_action}
                                    </p>
                                </div>
                            </div>
                        )}

                        {caseRow.hitl_action && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">Human-In-The-Loop (HITL) Action</p>
                                <div className="p-3 bg-muted rounded-lg border border-muted-foreground/10">
                                    <p className="text-sm">
                                        {caseRow.hitl_action.toUpperCase()}
                                    </p>
                                </div>
                            </div>
                        )}

                        {caseRow.final_action && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">Final Action</p>
                                <Badge variant="outline" className={`text-sm ${getFinalActionColor(caseRow.final_action)}`}>
                                    {caseRow.final_action.replace(/_/g, " ").toUpperCase()}
                                </Badge>
                            </div>
                        )}
                    </div>

                    <Separator />

                    {/* Timestamps */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2">
                            <History className="h-4 w-4" />
                            Timeline
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="flex items-center gap-2">
                                <Clock className="h-4 w-4 text-muted-foreground" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Created At</p>
                                    <p className="text-sm">
                                        {caseRow.created_at ? new Date(caseRow.created_at).toLocaleString() : "N/A"}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <History className="h-4 w-4 text-muted-foreground" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Updated At</p>
                                    <p className="text-sm">
                                        {caseRow.updated_at ? new Date(caseRow.updated_at).toLocaleString() : "N/A"}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <DialogFooter className="pt-4 border-t">
                    <Button variant="outline" onClick={onClose}>
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
