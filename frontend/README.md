# NexusAgent Frontend

A visual interface for NexusAgent built with React + TypeScript + Vite.

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Feature Overview](#feature-overview)
- [API Endpoints](#api-endpoints)
- [Code Architecture](#code-architecture)
- [Component Reference](#component-reference)
- [State Management](#state-management)
- [Development Guide](#development-guide)

---

## Requirements

- Node.js >= 18.x
- npm >= 9.x

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

After starting, visit http://localhost:5173

### 3. Build for Production

```bash
npm run build
```

Build output will be in the `dist/` directory.

### Startup Order

1. Start the backend API service first (default port 8000)
2. Then start the frontend development server (default port 5173)

```bash
# Terminal 1: Start the backend
cd /project-root
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

---

## Feature Overview

### Four-Column Layout

The interface is divided into four main areas, from left to right:

| Area | Name | Function |
|------|------|----------|
| 1 | Agent Interaction | Real-time chat interface with the Agent |
| 2 | Runtime | Tab switching between Execution (execution steps) and Narrative (conversation history) |
| 3 | Context | Agent Awareness, Social Network, and Workspace Files |
| 4 | Data | Tab switching between Inbox (messages) and Jobs (tasks) |

### Detailed Features

#### 1. Agent Interaction (Chat Panel)

- Real-time WebSocket streaming response
- Markdown rendering support
- Code syntax highlighting
- Message bubbles distinguishing User/Agent
- Auto-scroll to latest message

#### 2. Runtime Panel

**Execution Tab**:
- Real-time display of Agent execution steps
- Step status indicators (running/completed/failed)
- Progress count (completed/total)
- Expandable step details

**Narrative Tab**:
- Grouped display by Narrative (conversation topic)
- Narrative list sorted by update time
- Click to expand and show all Events under that Narrative
- Each Event is expandable to show:
  - User input
  - Agent response (Markdown)
  - Event Log (execution log)
  - Metadata

#### 3. Context Panel

**Agent Awareness Section**:
- Displays the Agent's self-awareness information
- Markdown rendering
- Last updated time

**Social Network Section**:
- Displays all contacts in the Agent's network
- Current user highlighted and marked as "Current"
- Sorted by actual chat count (calculated from chatHistoryEvents)
- Each contact is expandable to show:
  - Description
  - Tags
  - Identity Info
  - Contact Info
  - Relationship strength and interaction statistics

**Workspace Files Section**:
- Drag & Drop file upload
- Click to browse and select files for upload
- File list display (filename, size)
- File deletion
- File storage path: `./agent_workspace/{agent_id}_{user_id}/`

#### 4. Data Panel

**Inbox Tab**:
- Displays messages/notifications sent by the Agent
- Unread message count badge
- Click to expand and view full content
- Mark as read / Mark all as read
- Refresh

**Jobs Tab**:
- Displays scheduled and running tasks
- Status filter (all/active/running/pending/completed/failed)
- Task status indicator icons
- Click to expand and view:
  - Task type (one-off/scheduled)
  - Trigger configuration
  - Next/last run time
  - Error information

#### 5. Sidebar

- **Create Agent**: Click the + button to create a new Agent (auto-generated ID)
- Agent list display and selection
- Refresh Agent list
- Current user information display
- Clear conversation history
- Theme switching (Light/Dark/System)
- Logout

#### 6. Data Preloading

- **Parallel** preloading of all data on page load
- Data cached in Zustand Store
- No waiting when switching tabs
- Manual refresh support

---

## API Endpoints

### Backend API Endpoints

Backend service runs on `http://localhost:8000`

#### Authentication API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login |
| GET | `/api/auth/agents` | Get all Agent list |
| POST | `/api/auth/agents` | Create new Agent |

#### Agent API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/{agent_id}/awareness` | Get Agent Awareness |
| GET | `/api/agents/{agent_id}/social-network` | Get all social network contacts |
| GET | `/api/agents/{agent_id}/social-network/{user_id}` | Get social info for a specific user |
| GET | `/api/agents/{agent_id}/chat-history?user_id=xxx` | Get chat history (Narratives + Events) |
| DELETE | `/api/agents/{agent_id}/history?user_id=xxx` | Clear conversation history |

#### File Management API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/{agent_id}/files?user_id=xxx` | Get workspace file list |
| POST | `/api/agents/{agent_id}/files?user_id=xxx` | Upload file (multipart/form-data) |
| DELETE | `/api/agents/{agent_id}/files/{filename}?user_id=xxx` | Delete file |

#### Jobs API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs/{agent_id}?user_id=xxx&status=xxx` | Get task list |
| GET | `/api/jobs/{job_id}` | Get task details |

#### Inbox API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/inbox/{user_id}?is_read=xxx` | Get inbox messages |
| PUT | `/api/inbox/{message_id}/read` | Mark message as read |
| PUT | `/api/inbox/{user_id}/read-all` | Mark all messages as read |

#### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/agent/run` | Agent real-time execution stream |

### Frontend API Client

Location: `src/lib/api.ts`

```typescript
// Usage examples
import { api } from '@/lib/api';

// Auth
await api.login(userId);
await api.getAgents(userId);
await api.createAgent(createdBy, agentName?, agentDescription?);

// Agents
await api.getAwareness(agentId);
await api.getSocialNetwork(agentId, userId);
await api.getSocialNetworkList(agentId);
await api.getChatHistory(agentId, userId);
await api.clearHistory(agentId, userId);

// File Management
await api.listFiles(agentId, userId);
await api.uploadFile(agentId, userId, file);
await api.deleteFile(agentId, userId, filename);

// Jobs
await api.getJobs(agentId, userId, status);
await api.getJob(jobId);

// Inbox
await api.getInbox(userId, isRead);
await api.markMessageRead(messageId);
await api.markAllRead(userId);
```

---

## Code Architecture

### Directory Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── ui/               # Common UI components (Button, Card, Badge, etc.)
│   │   ├── chat/             # Chat-related components
│   │   │   ├── ChatPanel.tsx    # Chat main panel
│   │   │   └── MessageBubble.tsx # Message bubble
│   │   ├── layout/           # Layout components
│   │   │   ├── MainLayout.tsx   # Main layout (four-column)
│   │   │   └── Sidebar.tsx      # Sidebar
│   │   ├── runtime/          # Runtime panel components
│   │   │   ├── RuntimePanel.tsx # Execution/Narrative tab panel
│   │   │   ├── NarrativeList.tsx # Narrative list
│   │   │   ├── EventCard.tsx    # Event detail card
│   │   │   └── ...
│   │   ├── awareness/        # Context panel components
│   │   │   ├── AwarenessPanel.tsx # Awareness + Social Network + Files
│   │   │   └── FileUpload.tsx   # File upload component
│   │   ├── steps/            # Execution step components
│   │   │   ├── StepsPanel.tsx   # Steps panel
│   │   │   └── StepCard.tsx     # Step card
│   │   ├── history/          # History components
│   │   │   └── HistoryPanel.tsx # History panel (legacy)
│   │   ├── inbox/            # Inbox components
│   │   │   └── InboxPanel.tsx   # Inbox panel
│   │   └── jobs/             # Jobs components
│   │       └── JobsPanel.tsx    # Jobs panel
│   │
│   ├── stores/               # Zustand state management
│   │   ├── configStore.ts    # Config state (login, Agent selection)
│   │   ├── chatStore.ts      # Chat state (messages, steps)
│   │   ├── preloadStore.ts   # Preload cache (Inbox, Jobs, Awareness, etc.)
│   │   └── index.ts
│   │
│   ├── hooks/                # Custom Hooks
│   │   ├── useWebSocket.ts   # WebSocket connection Hook
│   │   ├── useTheme.ts       # Theme management Hook
│   │   └── index.ts
│   │
│   ├── lib/                  # Utility library
│   │   ├── api.ts            # API client
│   │   └── utils.ts          # Utility functions
│   │
│   ├── types/                # TypeScript type definitions
│   │   ├── api.ts            # API response types
│   │   ├── messages.ts       # Message-related types
│   │   └── index.ts
│   │
│   ├── pages/                # Page components
│   │   └── LoginPage.tsx     # Login page
│   │
│   ├── App.tsx               # Application entry (routing config)
│   ├── main.tsx              # Render entry
│   └── index.css             # Global styles (CSS variables)
│
├── public/                   # Static assets
├── index.html                # HTML template
├── package.json              # Dependency config
├── vite.config.ts            # Vite config
├── tailwind.config.js        # Tailwind config
└── tsconfig.json             # TypeScript config
```

### Data Flow

```
User Action
    ↓
Component (React Component)
    ↓
Zustand Store (State Management)
    ↓
API Client / WebSocket Hook
    ↓
Backend API
    ↓
Data Response
    ↓
Store Update
    ↓
Component Re-render
```

### Preloading Mechanism

```
Page Load (MainLayout mount)
    ↓
useEffect triggers preloadAll()
    ↓
Promise.allSettled() parallel requests
    ├─→ api.getInbox()
    ├─→ api.getJobs()
    ├─→ api.getAwareness()
    ├─→ api.getSocialNetworkList()
    └─→ api.getChatHistory()
    ↓
Data stored in preloadStore
    ↓
Panel components read from preloadStore
    ↓
Cached data used instantly when switching tabs (no waiting)
```

---

## Component Reference

### UI Components (`src/components/ui/`)

| Component | Description |
|-----------|-------------|
| `Button` | Button component, supports variant/size/disabled |
| `Card` | Card container, includes CardHeader/CardTitle/CardContent |
| `Badge` | Badge component, supports variant/size/pulse |
| `Input` | Input field |
| `Textarea` | Multi-line text field |
| `Select` | Dropdown select |
| `Markdown` | Markdown rendering component |

### Business Components

| Component | Location | Description |
|-----------|----------|-------------|
| `MainLayout` | layout/ | Main layout with four columns + sidebar |
| `Sidebar` | layout/ | Sidebar for Agent selection/creation and user info |
| `ChatPanel` | chat/ | Chat panel with WebSocket message stream |
| `MessageBubble` | chat/ | Message bubble |
| `RuntimePanel` | runtime/ | Execution/Narrative tab panel |
| `NarrativeList` | runtime/ | Narrative list |
| `EventCard` | runtime/ | Event detail card |
| `AwarenessPanel` | awareness/ | Awareness + Social Network + Files |
| `FileUpload` | awareness/ | Drag & drop file upload component |
| `StepsPanel` | steps/ | Execution steps panel |
| `StepCard` | steps/ | Individual step card |
| `InboxPanel` | inbox/ | Inbox panel |
| `JobsPanel` | jobs/ | Jobs panel |

---

## State Management

Uses Zustand for state management, divided into three Stores:

### configStore

Manages global configuration and authentication state.

```typescript
interface ConfigState {
  isLoggedIn: boolean;
  userId: string;
  agentId: string;
  agents: AgentInfo[];

  login(userId: string): void;
  logout(): void;
  setAgentId(id: string): void;
  setAgents(agents: AgentInfo[]): void;
}
```

**Persistence**: Uses localStorage, key is `nexus-agent-config`

### chatStore

Manages chat-related state.

```typescript
interface ChatState {
  messages: ChatMessage[];
  currentSteps: Step[];
  currentThinking: string;
  currentToolCalls: AgentToolCall[];
  history: ConversationRound[];
  isStreaming: boolean;
  currentAssistantMessage: string;

  addUserMessage(content: string): void;
  processMessage(message: RuntimeMessage): void;
  startStreaming(): void;
  stopStreaming(): void;
  saveToHistory(): void;
  clearCurrent(): void;
  clearAll(): void;
}
```

### preloadStore

Manages preloaded cached data.

```typescript
interface PreloadState {
  // Data
  inbox: InboxMessage[];
  inboxUnreadCount: number;
  jobs: Job[];
  awareness: string | null;
  awarenessCreateTime: string | null;
  awarenessUpdateTime: string | null;
  socialNetworkList: SocialNetworkEntity[];
  chatHistoryEvents: ChatHistoryEvent[];
  chatHistoryNarratives: ChatHistoryNarrative[];

  // Loading states
  inboxLoading: boolean;
  jobsLoading: boolean;
  awarenessLoading: boolean;
  socialNetworkLoading: boolean;
  chatHistoryLoading: boolean;

  // Error states
  inboxError: string | null;
  jobsError: string | null;
  awarenessError: string | null;
  socialNetworkError: string | null;
  chatHistoryError: string | null;

  // Methods
  preloadAll(agentId: string, userId: string): Promise<void>;
  refreshInbox(userId: string): Promise<void>;
  refreshJobs(agentId: string, userId: string, status?: string): Promise<void>;
  refreshAwareness(agentId: string): Promise<void>;
  refreshSocialNetwork(agentId: string): Promise<void>;
  refreshChatHistory(agentId: string, userId: string): Promise<void>;
  addChatHistoryEvent(event: ChatHistoryEvent): void;
  updateInboxMessage(messageId: string, updates: Partial<InboxMessage>): void;
  markAllInboxRead(): void;
  clearAll(): void;
}
```

---

## Development Guide

### Adding a New API Endpoint

1. Add response types in `src/types/api.ts`
2. Add API methods in `src/lib/api.ts`
3. If preloading is needed, update `src/stores/preloadStore.ts`

### Adding a New Component

1. Create a directory under `src/components/`
2. Create the component file and `index.ts` export
3. Import and use where needed

### Adding a New Panel

1. Create the panel component
2. Add layout position in `MainLayout.tsx`
3. If data preloading is needed, update `preloadStore`

### Style Guidelines

Use CSS variables to ensure theme consistency:

```css
/* Background colors */
var(--bg-primary)
var(--bg-secondary)
var(--bg-tertiary)
var(--bg-elevated)

/* Text colors */
var(--text-primary)
var(--text-secondary)
var(--text-tertiary)

/* Border colors */
var(--border-default)
var(--border-muted)

/* Accent colors */
var(--color-accent)
var(--color-success)
var(--color-error)
var(--color-warning)

/* Opacity variants */
var(--accent-10)  /* 10% opacity */
```

### Common Commands

| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies |
| `npm run dev` | Start development server (hot reload) |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint checks |

---

## Tech Stack

- **React 19** - UI framework
- **TypeScript 5.9** - Type safety
- **Vite 7.2** - Build tool
- **Tailwind CSS 4.1** - CSS framework
- **Zustand 5.0** - State management
- **React Router 7.9** - Routing
- **Lucide React** - Icon library
- **react-markdown** - Markdown rendering

---

## Configuration Files

### Vite Proxy Configuration

In development mode, Vite automatically proxies API requests:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true,
    },
  },
}
```

### Path Aliases

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Usage examples:
```typescript
import { Button } from '@/components/ui';
import { useConfigStore } from '@/stores';
```
