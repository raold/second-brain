# Second Brain Frontend

A modern web interface for the Second Brain v4.2 API built with SvelteKit, TypeScript, and Tailwind CSS.

## Features

- **Memory Management**: Create, edit, delete, and search memories
- **Vector Search**: Semantic search powered by OpenAI embeddings
- **Hybrid Search**: Combine vector similarity with full-text search
- **Real-time Updates**: WebSocket integration for live updates
- **Knowledge Graph**: Interactive visualization of memory connections
- **Dark Mode**: Built-in dark mode support
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Framework**: SvelteKit 2.0
- **Language**: TypeScript
- **Styling**: Tailwind CSS 3.4
- **State Management**: Svelte stores
- **API Client**: Custom TypeScript client
- **WebSockets**: Real-time updates
- **Build Tool**: Vite

## Project Structure

```
frontend/
├── src/
│   ├── lib/
│   │   ├── api/          # API client and WebSocket
│   │   ├── components/   # Reusable Svelte components
│   │   ├── stores/       # Svelte stores for state
│   │   └── types/        # TypeScript type definitions
│   ├── routes/           # SvelteKit pages
│   │   ├── +layout.svelte
│   │   ├── +page.svelte  # Home/Search page
│   │   ├── memories/     # Memory management pages
│   │   └── visualize/    # Knowledge graph
│   └── app.css           # Global styles
├── static/               # Static assets
└── package.json
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Second Brain API running on port 8000

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at http://localhost:5173

### Build

```bash
npm run build
npm run preview
```

## Key Components

### SearchBar
- Debounced search input
- Configurable placeholder

### MemoryCard
- Displays memory content, tags, importance
- Shows search scores for results
- Actions: view, edit, delete

### API Client (`lib/api/client.ts`)
- Full TypeScript API client
- All v4.2 endpoints implemented
- Error handling and type safety

### WebSocket Client (`lib/api/websocket.ts`)
- Auto-reconnection with exponential backoff
- Real-time memory updates
- Connection state management

### Stores (`lib/stores/memories.ts`)
- Reactive state management
- Derived stores for computed values
- Helper functions for mutations

## Pages

### Home (`/`)
- Search interface
- Toggle between vector and hybrid search
- Adjustable vector weight for hybrid search
- Real-time search results

### Memories (`/memories`)
- List all memories
- Filter by type and tags
- Sort by date, access count, or importance
- Bulk operations

### New Memory (`/memories/new`)
- Create form with all fields
- Tag input with comma separation
- Importance slider
- Real-time validation

### Memory Detail (`/memories/[id]`)
- Full memory content
- Metadata display
- Related memories (vector similarity)
- Edit and delete actions

### Visualize (`/visualize`)
- Force-directed graph
- Node size by importance
- Links by shared tags
- Interactive canvas

## Configuration

### API Endpoint
The API endpoint is configured in `lib/api/client.ts`:
```typescript
const API_BASE = 'http://localhost:8000/api/v2';
```

### WebSocket
WebSocket URL is auto-detected from current host:
```typescript
const wsUrl = `${protocol}//${window.location.host}/api/v2/ws`;
```

## Deployment

### Docker
```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./
RUN npm ci --production
EXPOSE 3000
CMD ["node", "build"]
```

### Environment Variables
Create `.env` for production:
```
PUBLIC_API_URL=https://api.example.com
NODE_ENV=production
```

## Future Enhancements

- [ ] Authentication/authorization
- [ ] Memory export/import
- [ ] Advanced filtering UI
- [ ] Batch operations
- [ ] Keyboard shortcuts
- [ ] Memory templates
- [ ] Rich text editor
- [ ] File attachments
- [ ] Sharing capabilities
- [ ] Mobile app

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm test`
5. Submit a pull request

## License

MIT License - see LICENSE file