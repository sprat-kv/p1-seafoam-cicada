"use client";

import { Badge } from "@/components/ui/badge";
import { FileText, Scale } from "lucide-react";
import { AppliedPolicy } from "@/lib/types";

interface PolicyInformationProps {
    policies?: AppliedPolicy[] | null;
}

const COMPLIANCE_STYLES: Record<NonNullable<AppliedPolicy["compliance"]>, string> = {
    compliant:
        "border-green-200/60 text-green-700 dark:text-green-300",
    non_compliant:
        "border-red-200/60 text-red-700 dark:text-red-300",
    requires_review:
        "border-amber-200/60 text-amber-700 dark:text-amber-300",
};

function getComplianceLabel(compliance?: AppliedPolicy["compliance"]) {
    if (!compliance) return "Unknown";
    return compliance.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function PolicyInformation({ policies }: PolicyInformationProps) {
    if (!policies?.length) return null;

    return (
        <div>
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-2">
                <Scale className="h-4 w-4" />
                Policy Information
            </h3>
            <div className="rounded-lg border border-muted overflow-hidden">
                {policies.map((policy, index) => (
                    <div
                        key={`${policy.source}-${index}`}
                        className="p-3 space-y-2 bg-background"
                    >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0">
                                <p className="text-sm font-medium">{policy.title || policy.source}</p>
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <FileText className="h-3 w-3" />
                                    {policy.source}
                                </p>
                            </div>
                            <Badge
                                variant="outline"
                                className={`bg-transparent text-[11px] font-medium ${COMPLIANCE_STYLES[policy.compliance ?? "requires_review"]}`}
                            >
                                {getComplianceLabel(policy.compliance)}
                            </Badge>
                        </div>
                        {policy.cited_rule && (
                            <p className="text-sm leading-relaxed text-foreground/90">
                                {policy.cited_rule}
                            </p>
                        )}
                        {index < policies.length - 1 && <div className="border-b border-muted" />}
                    </div>
                ))}
            </div>
        </div>
    );
}
