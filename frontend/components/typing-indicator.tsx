export function TypingIndicator() {
    return (
        <div className="flex items-center space-x-2 px-4 py-3 bg-muted rounded-lg max-w-[80px]">
            <div className="flex space-x-1">
                <div className="w-2 h-2 bg-foreground/60 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-foreground/60 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-foreground/60 rounded-full animate-bounce"></div>
            </div>
        </div>
    );
}
