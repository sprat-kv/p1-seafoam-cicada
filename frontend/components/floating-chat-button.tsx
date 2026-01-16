"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { TriageChat } from "./triage-chat";
import { MessageCircle, Minus } from "lucide-react";

export function FloatingChatButton() {
    const [isOpen, setIsOpen] = useState(false);
    const [hasActiveSession, setHasActiveSession] = useState(false);

    const handleOpen = () => {
        setIsOpen(true);
    };

    const handleMinimize = () => {
        setIsOpen(false);
        // Keep session active
    };

    const handleClose = () => {
        setIsOpen(false);
        setHasActiveSession(false);
    };

    const handleSessionStart = () => {
        setHasActiveSession(true);
    };

    return (
        <>
            {!isOpen && (
                <Button
                    onClick={handleOpen}
                    className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-all z-50 group"
                    size="icon"
                    aria-label="Open chat"
                >
                    <MessageCircle className="h-6 w-6 transition-transform group-hover:scale-110" />
                    {hasActiveSession && (
                        <span className="absolute -top-1 -right-1 flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                        </span>
                    )}
                </Button>
            )}

            <TriageChat
                isOpen={isOpen}
                onMinimize={handleMinimize}
                onClose={handleClose}
                onSessionStart={handleSessionStart}
            />
        </>
    );
}
