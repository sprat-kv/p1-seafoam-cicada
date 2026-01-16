# Triage Support System - Frontend

A modern, minimal Next.js frontend for the Triage Agent system with AI-powered customer support and human-in-the-loop ticket review.

## Features

- 🤖 **Floating Chat Bot** - Global chat component with multi-turn conversations
- ✅ **Thread Persistence** - Conversations maintained across sessions
- 💬 **Typing Indicators** - Real-time feedback during agent responses
- 🎫 **Admin Dashboard** - Modern ticket review interface
- ✓ **Approve/Reject** - Quick ticket resolution with visual feedback
- 🎨 **Modern UI** - Built with Tailwind CSS and Shadcn UI
- 📱 **Responsive** - Works on mobile, tablet, and desktop

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: Shadcn UI
- **Icons**: Lucide React
- **API Integration**: Native fetch with error handling

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Backend API running on `http://localhost:8000` (or configured URL)

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Update API URL if needed
# Edit .env.local and set NEXT_PUBLIC_API_URL
```

### Development

```bash
# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

```
├── app/
│   ├── admin/           # Admin dashboard page
│   ├── layout.tsx       # Root layout with FloatingChatButton
│   ├── page.tsx         # Home page
│   └── globals.css      # Global styles
├── components/
│   ├── ui/              # Shadcn UI components
│   ├── floating-chat-button.tsx
│   ├── triage-chat.tsx
│   ├── message-bubble.tsx
│   ├── typing-indicator.tsx
│   ├── ticket-card.tsx
│   └── ticket-detail.tsx
├── lib/
│   ├── types.ts         # TypeScript definitions
│   └── api.ts           # API service layer
└── .env.local           # Environment variables
```

## Usage

### Customer Chat

1. Click the floating chat button in the bottom-right corner on any page
2. Type your message describing your issue (e.g., "I need a refund for order ORD1001")
3. The agent will respond and guide you through the process
4. Click "End Conversation" when done

### Admin Dashboard

1. Navigate to `/admin` or click "Admin Dashboard" from the home page
2. View all pending tickets in a card layout
3. Click on a ticket to view details
4. Click "Approve" or "Reject" to process the ticket
5. Use the "Refresh" button to manually update the ticket list

## Environment Variables

Create a `.env.local` file with:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Change the URL to match your backend API endpoint.

## API Endpoints

The frontend expects these backend endpoints:

- `POST /triage/invoke` - Start or continue a chat conversation
- `GET /admin/review` - List all pending tickets
- `POST /admin/review?thread_id={id}` - Submit admin review decision

See [docs/openapi.json](docs/openapi.json) for full API documentation.

## Key Features

### Chat Component
- Multi-turn conversations with context
- Thread ID persistence in localStorage
- Typing indicators during API calls
- Conversation ended state with success feedback
- Auto-scroll to latest message
- Keyboard support (Enter to send)

### Admin Dashboard
- Clean, modern interface
- Ticket count display
- Manual refresh
- Empty state handling
- Responsive grid layout
- Loading states

### Ticket Details
- Comprehensive information display
- Order and customer details
- Issue type and suggested action
- Draft reply preview
- Approve (green) and Reject (red) buttons
- Success/error feedback
- Auto-close on completion

## Troubleshooting

### Chat not connecting to backend

1. Verify backend is running on the configured URL
2. Check `.env.local` has correct `NEXT_PUBLIC_API_URL`
3. Open browser console for error messages
4. Verify CORS is enabled on backend

### Admin dashboard shows no tickets

1. Ensure backend API is running
2. Create a ticket by using the chat first
3. Click the Refresh button
4. Check browser console for errors

### Development server won't start

```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Try again
npm run dev
```

## Development

Built with modern best practices:

- TypeScript for type safety
- Component-based architecture
- Responsive design
- Error boundaries
- Loading states
- Accessibility considerations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the Triage Support System.

---

**Documentation**: See [walkthrough.md](../../.gemini/antigravity/brain/c4274e42-73a9-4fcf-a64e-9d3d4248dd6e/walkthrough.md) for detailed feature documentation.
