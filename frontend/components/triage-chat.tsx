"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardHeader } from "@/components/ui/card";
import { MessageBubble } from "./message-bubble";
import { TypingIndicator } from "./typing-indicator";
import { triageInvoke } from "@/lib/api";
import { Message } from "@/lib/types";
import { Send, CheckCircle2, Minus, X } from "lucide-react";

interface TriageChatProps {
    isOpen: boolean;
    onMinimize: () => void;
    onClose: () => void;
    onSessionStart: () => void;
}

const THREAD_ID_KEY = "triage_thread_id";

export function TriageChat({ isOpen, onMinimize, onClose, onSessionStart }: TriageChatProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [threadId, setThreadId] = useState<string | null>(null);
    const [conversationEnded, setConversationEnded] = useState(false);
    const scrollAreaRef = useRef<HTMLDivElement>(null);

    // Load thread_id from localStorage on mount
    useEffect(() => {
        const savedThreadId = localStorage.getItem(THREAD_ID_KEY);
        if (savedThreadId) {
            setThreadId(savedThreadId);
        }
    }, []);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        if (scrollAreaRef.current) {
            const scrollContainer = scrollAreaRef.current.querySelector(
                "[data-radix-scroll-area-viewport]"
            );
            if (scrollContainer) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        }
    }, [messages, isLoading]);

    const handleSendMessage = async () => {
        if (!input.trim() || isLoading || conversationEnded) return;

        const userMessage: Message = {
            role: "user",
            content: input.trim(),
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);

        // Notify parent that session has started
        if (messages.length === 0) {
            onSessionStart();
        }

        try {
            const response = await triageInvoke({
                ticket_text: userMessage.content,
                thread_id: threadId,
            });

            // Save thread_id
            if (response.thread_id && response.thread_id !== threadId) {
                setThreadId(response.thread_id);
                localStorage.setItem(THREAD_ID_KEY, response.thread_id);
            }

            // Add agent response
            const agentMessage: Message = {
                role: "assistant",
                content: response.draft_reply || response.reply_text || "Processing your request...",
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, agentMessage]);
        } catch (error) {
            console.error("Error sending message:", error);
            const errorMessage: Message = {
                role: "assistant",
                content:
                    "Sorry, I encountered an error. Please try again or contact support.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        setConversationEnded(true);
    };

    const handleEndSession = () => {
        setMessages([]);
        setThreadId(null);
        localStorage.removeItem(THREAD_ID_KEY);
        setConversationEnded(false);
        onClose();
    };

    const handleNewConversation = () => {
        setMessages([]);
        setThreadId(null);
        localStorage.removeItem(THREAD_ID_KEY);
        setConversationEnded(false);
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    if (!isOpen) return null;

    return (
        <Card className="fixed bottom-24 right-6 w-[400px] max-w-[calc(100vw-48px)] h-[600px] max-h-[calc(100vh-200px)] shadow-2xl flex flex-col z-40 border-primary/20 animate-in slide-in-from-bottom-10 fade-in-0">
            {/* Header */}
            <CardHeader className="px-4 py-3 border-b bg-primary/5 shrink-0">
                <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-sm flex items-center gap-2">
                        <span className="relative flex h-2.5 w-2.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                        </span>
                        Customer Support
                    </h3>
                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={onMinimize}
                            className="h-7 w-7 hover:bg-muted"
                            title="Minimize"
                        >
                            <Minus className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleEndSession}
                            className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive"
                            title="Close Chat"
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </CardHeader>

            {/* Conversation Ended State */}
            {conversationEnded ? (
                <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-4 animate-in fade-in-50 zoom-in-95">
                    <div className="bg-green-100 dark:bg-green-900/30 p-4 rounded-full mb-2">
                        <CheckCircle2 className="h-10 w-10 text-green-600 dark:text-green-500" />
                    </div>
                    <h3 className="text-lg font-semibold text-center">Conversation Ended</h3>
                    <p className="text-sm text-muted-foreground text-center max-w-[250px]">
                        Thank you for contacting support. Your ticket has been submitted for review.
                    </p>
                    <Button onClick={handleNewConversation} className="mt-4 w-full">
                        Start New Conversation
                    </Button>
                </div>
            ) : (
                <>
                    {/* Messages Area */}
                    <ScrollArea className="flex-1 min-h-0" ref={scrollAreaRef}>
                        <div className="px-4 py-4">
                            {messages.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-[400px] text-center text-muted-foreground opacity-70">
                                    <p className="text-sm">Hi! I'm here to help with your order issues.</p>
                                    <p className="text-sm mt-1">How can I assist you today?</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {messages.map((message, index) => (
                                        <MessageBubble key={index} message={message} />
                                    ))}
                                    {isLoading && (
                                        <div className="flex gap-2 items-center text-muted-foreground text-xs">
                                            <span className="h-6 w-6 flex items-center justify-center rounded-full bg-muted border text-sm">🤖</span>
                                            <TypingIndicator />
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </ScrollArea>

                    {/* Input Area - Always Visible at Bottom */}
                    <div className="border-t bg-background p-4 shrink-0">
                        <div className="flex gap-2 mb-2">
                            <Input
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Type your message..."
                                disabled={isLoading}
                                className="flex-1"
                            />
                            <Button
                                onClick={handleSendMessage}
                                disabled={!input.trim() || isLoading}
                                size="icon"
                            >
                                <Send className="h-4 w-4" />
                            </Button>
                        </div>
                        <div className="flex justify-center">
                            <Button
                                onClick={handleClose}
                                variant="ghost"
                                size="sm"
                                className="text-xs h-6 text-muted-foreground hover:text-destructive"
                            >
                                End Conversation
                            </Button>
                        </div>
                    </div>
                </>
            )}
        </Card>
    );
}
