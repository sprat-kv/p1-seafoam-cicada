import Link from "next/link";
import { Button } from "@/components/ui/button";
import { MessageCircle, Shield, Zap, CheckCircle } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="max-w-4xl mx-auto text-center py-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full mb-6">
            <Zap className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">
              AI-Powered Support
            </span>
          </div>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
            Triage Support System
          </h1>

          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Intelligent ticket triage with human-in-the-loop review.
            Fast, efficient, and always accurate customer support.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link href="/admin">
              <Button size="lg" className="gap-2">
                <Shield className="h-5 w-5" />
                Admin Dashboard
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="gap-2" disabled>
              <MessageCircle className="h-5 w-5" />
              Chat (Use floating button)
            </Button>
          </div>
        </div>

        {/* Features */}
        <div className="max-w-5xl mx-auto mt-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-lg border bg-card hover:shadow-lg transition-all">
              <div className="bg-primary/10 w-12 h-12 rounded-full flex items-center justify-center mb-4">
                <MessageCircle className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Multi-turn Conversations</h3>
              <p className="text-sm text-muted-foreground">
                Context-aware chatbot that maintains conversation history across sessions
              </p>
            </div>

            <div className="p-6 rounded-lg border bg-card hover:shadow-lg transition-all">
              <div className="bg-primary/10 w-12 h-12 rounded-full flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Human-in-the-Loop</h3>
              <p className="text-sm text-muted-foreground">
                Admin review checkpoint ensures accuracy before final responses
              </p>
            </div>

            <div className="p-6 rounded-lg border bg-card hover:shadow-lg transition-all">
              <div className="bg-primary/10 w-12 h-12 rounded-full flex items-center justify-center mb-4">
                <CheckCircle className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Smart Classification</h3>
              <p className="text-sm text-muted-foreground">
                Intelligent issue detection with priority-based routing
              </p>
            </div>
          </div>
        </div>

        {/* CTA at bottom */}
        <div className="max-w-3xl mx-auto text-center mt-20 p-8 rounded-2xl bg-muted/30 border">
          <h2 className="text-2xl font-bold mb-4">Get Started</h2>
          <p className="text-muted-foreground mb-6">
            Click the floating chat button in the bottom-right corner to start a conversation,
            or access the admin dashboard to review pending tickets.
          </p>
          <Link href="/admin">
            <Button size="lg" variant="default">
              Go to Admin Dashboard
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
