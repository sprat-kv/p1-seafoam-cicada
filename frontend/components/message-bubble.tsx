import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Message } from "@/lib/types";
import { Bot, User } from "lucide-react";

interface MessageBubbleProps {
    message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === "user";

    return (
        <div
            className={`flex gap-3 mb-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}
        >
            <Avatar className="h-8 w-8 shrink-0">
                <AvatarFallback className={isUser ? "bg-primary" : "bg-muted"}>
                    {isUser ? (
                        <User className="h-4 w-4 text-primary-foreground" />
                    ) : (
                        <Bot className="h-4 w-4 text-muted-foreground" />
                    )}
                </AvatarFallback>
            </Avatar>
            <div
                className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[75%]`}
            >
                <div
                    className={`px-4 py-2 rounded-lg ${isUser
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-foreground"
                        }`}
                >
                    <p className="text-sm whitespace-pre-wrap break-words">
                        {message.content}
                    </p>
                </div>
                {message.timestamp && (
                    <span className="text-xs text-muted-foreground mt-1 px-1">
                        {new Date(message.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                        })}
                    </span>
                )}
            </div>
        </div>
    );
}
