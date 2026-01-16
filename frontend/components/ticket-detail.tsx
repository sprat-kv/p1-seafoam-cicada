"use client";

import { useState } from "react";
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
import { PendingTicket } from "@/lib/types";
import { submitReview } from "@/lib/api";
import { Check, X, Loader2, Package, User, MessageSquare } from "lucide-react";

interface TicketDetailProps {
    ticket: PendingTicket | null;
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export function TicketDetail({
    ticket,
    isOpen,
    onClose,
    onSuccess,
}: TicketDetailProps) {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitStatus, setSubmitStatus] = useState<"idle" | "success" | "error">("idle");

    if (!ticket) return null;

    const handleApprove = async () => {
        setIsSubmitting(true);
        setSubmitStatus("idle");
        try {
            await submitReview(ticket.thread_id, {
                status: "approved",
                feedback: "Approved",
            });
            setSubmitStatus("success");
            setTimeout(() => {
                onSuccess();
                onClose();
                setSubmitStatus("idle");
            }, 1000);
        } catch (error) {
            console.error("Error approving ticket:", error);
            setSubmitStatus("error");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleReject = async () => {
        setIsSubmitting(true);
        setSubmitStatus("idle");
        try {
            await submitReview(ticket.thread_id, {
                status: "rejected",
                feedback: "Rejected",
            });
            setSubmitStatus("success");
            setTimeout(() => {
                onSuccess();
                onClose();
                setSubmitStatus("idle");
            }, 1000);
        } catch (error) {
            console.error("Error rejecting ticket:", error);
            setSubmitStatus("error");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle className="text-2xl">Ticket Details</DialogTitle>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    {/* Order Information */}
                    <div className="space-y-2">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                            Order Information
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="flex items-center gap-2">
                                <Package className="h-4 w-4 text-muted-foreground" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Order ID</p>
                                    <p className="font-medium">{ticket.order_id || "N/A"}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-muted-foreground" />
                                <div>
                                    <p className="text-xs text-muted-foreground">Customer</p>
                                    <p className="font-medium">
                                        {ticket.customer_name || "Unknown"}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <Separator />

                    {/* Issue Type */}
                    {ticket.issue_type && (
                        <div>
                            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                                Issue Type
                            </h3>
                            <Badge variant="secondary" className="text-sm">
                                {ticket.issue_type.replace("_", " ").toUpperCase()}
                            </Badge>
                        </div>
                    )}

                    {/* Suggested Action */}
                    {ticket.suggested_action && (
                        <>
                            <Separator />
                            <div>
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                                    Suggested Action
                                </h3>
                                <div className="p-4 bg-muted rounded-lg">
                                    <p className="text-sm">{ticket.suggested_action}</p>
                                </div>
                            </div>
                        </>
                    )}

                    {/* Draft Reply */}
                    {ticket.draft_reply && (
                        <>
                            <Separator />
                            <div>
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-2">
                                    <MessageSquare className="h-4 w-4" />
                                    Draft Reply (Sent to Customer)
                                </h3>
                                <div className="p-4 bg-muted/50 rounded-lg border border-muted">
                                    <p className="text-sm whitespace-pre-wrap">
                                        {ticket.draft_reply}
                                    </p>
                                </div>
                            </div>
                        </>
                    )}

                    {/* Status Messages */}
                    {submitStatus === "success" && (
                        <div className="p-3 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 rounded-lg text-sm flex items-center gap-2">
                            <Check className="h-4 w-4" />
                            Successfully submitted!
                        </div>
                    )}
                    {submitStatus === "error" && (
                        <div className="p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-lg text-sm flex items-center gap-2">
                            <X className="h-4 w-4" />
                            Failed to submit. Please try again.
                        </div>
                    )}
                </div>

                <DialogFooter className="gap-2">
                    <Button
                        variant="outline"
                        onClick={onClose}
                        disabled={isSubmitting}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={handleReject}
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                            <X className="h-4 w-4 mr-2" />
                        )}
                        Reject
                    </Button>
                    <Button
                        onClick={handleApprove}
                        disabled={isSubmitting}
                        className="bg-green-600 hover:bg-green-700"
                    >
                        {isSubmitting ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                            <Check className="h-4 w-4 mr-2" />
                        )}
                        Approve
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
