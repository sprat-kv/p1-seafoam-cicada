import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PendingTicket } from "@/lib/types";
import { Package, User } from "lucide-react";

interface TicketCardProps {
    ticket: PendingTicket;
    onClick: () => void;
}

export function TicketCard({ ticket, onClick }: TicketCardProps) {
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
                            {ticket.order_id || "No Order ID"}
                        </span>
                    </div>
                    {ticket.issue_type && (
                        <Badge variant="outline" className="text-xs">
                            {ticket.issue_type.replace("_", " ").toUpperCase()}
                        </Badge>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <User className="h-3 w-3" />
                    <span>{ticket.customer_name || "Unknown Customer"}</span>
                </div>
                {ticket.suggested_action && (
                    <p className="text-sm text-foreground line-clamp-2">
                        <span className="font-medium">Action:</span>{" "}
                        {ticket.suggested_action}
                    </p>
                )}
                {ticket.created_at && (
                    <p className="text-xs text-muted-foreground">
                        {new Date(ticket.created_at).toLocaleString()}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
