"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { TicketCard } from "@/components/ticket-card";
import { TicketDetail } from "@/components/ticket-detail";
import { getPendingTickets } from "@/lib/api";
import { PendingTicket } from "@/lib/types";
import { RefreshCw, Inbox, Loader2, AlertCircle } from "lucide-react";

export default function AdminPage() {
    const [tickets, setTickets] = useState<PendingTicket[]>([]);
    const [selectedTicket, setSelectedTicket] = useState<PendingTicket | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchTickets = async () => {
        try {
            setIsRefreshing(true);
            setError(null);
            const response = await getPendingTickets();
            setTickets(response.tickets);
        } catch (error) {
            console.error("Error fetching tickets:", error);
            setError("Unable to connect to the backend API. Please ensure the backend server is running.");
        } finally {
            setIsLoading(false);
            setIsRefreshing(false);
        }
    };

    useEffect(() => {
        fetchTickets();
    }, []);

    const handleTicketClick = (ticket: PendingTicket) => {
        setSelectedTicket(ticket);
    };

    const handleCloseDetail = () => {
        setSelectedTicket(null);
    };

    const handleSuccess = () => {
        fetchTickets();
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-4xl font-bold tracking-tight mb-2">
                                Admin Dashboard
                            </h1>
                            <p className="text-muted-foreground">
                                Review and manage pending support tickets
                            </p>
                        </div>
                        <Button
                            onClick={fetchTickets}
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

                {/* Ticket Count */}
                {!error && (
                    <div className="mb-6">
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full">
                            <Inbox className="h-4 w-4 text-primary" />
                            <span className="text-sm font-medium">
                                {tickets.length} {tickets.length === 1 ? "Ticket" : "Tickets"} Pending
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
                        {tickets.length === 0 && !error ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center">
                                <div className="bg-muted/50 rounded-full p-6 mb-4">
                                    <Inbox className="h-12 w-12 text-muted-foreground" />
                                </div>
                                <h3 className="text-xl font-semibold mb-2">No Pending Tickets</h3>
                                <p className="text-muted-foreground max-w-md">
                                    All caught up! There are no tickets waiting for review at the moment.
                                </p>
                            </div>
                        ) : !error ? (
                            /* Ticket Grid */
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {tickets.map((ticket) => (
                                    <TicketCard
                                        key={ticket.thread_id}
                                        ticket={ticket}
                                        onClick={() => handleTicketClick(ticket)}
                                    />
                                ))}
                            </div>
                        ) : null}
                    </>
                )}
            </div>

            {/* Ticket Detail Modal */}
            <TicketDetail
                ticket={selectedTicket}
                isOpen={!!selectedTicket}
                onClose={handleCloseDetail}
                onSuccess={handleSuccess}
            />
        </div>
    );
}
