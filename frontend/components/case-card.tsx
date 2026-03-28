import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CaseHistoryRow } from "@/lib/types";
import { Package, User } from "lucide-react";

interface CaseCardProps {
    caseRow: CaseHistoryRow;
    onClick: () => void;
}

function getFinalActionColor(action: string | null) {
    if (!action) return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800";
    if (action.includes("approved")) return "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800";
    if (action.includes("rejected")) return "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800";
    return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800";
}

function getStatusColor(status: string | null) {
    if (status === "closed") return "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800";
    if (status === "in_review") return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800";
    return "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800";
}

export function CaseCard({ caseRow, onClick }: CaseCardProps) {
    return (
        <Card
            className="cursor-pointer hover:shadow-md transition-all hover:border-primary/50"
            onClick={onClick}
        >
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                        <Package className="h-4 w-4 text-muted-foreground" />
                        <span className="font-semibold text-sm">
                            {caseRow.order_id || "No Order ID"}
                        </span>
                    </div>
                    {caseRow.final_action ? (
                        <Badge variant="outline" className={`text-xs ${getFinalActionColor(caseRow.final_action)}`}>
                            {caseRow.final_action.replace(/_/g, " ").toUpperCase()}
                        </Badge>
                    ) : caseRow.status ? (
                        <Badge variant="outline" className={`text-xs ${getStatusColor(caseRow.status)}`}>
                            {caseRow.status.replace(/_/g, " ").toUpperCase()}
                        </Badge>
                    ) : null}
                </div>
            </CardHeader>
            <CardContent className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <User className="h-3 w-3" />
                    <span>{caseRow.customer_name || "Unknown Customer"}</span>
                </div>
                {caseRow.decision_maker_action && (
                    <p className="text-sm text-foreground line-clamp-2">
                        <span className="font-medium">Action:</span>{" "}
                        {caseRow.decision_maker_action}
                    </p>
                )}
                {caseRow.updated_at && (
                    <p className="text-xs text-muted-foreground">
                        {new Date(caseRow.updated_at).toLocaleString()}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
