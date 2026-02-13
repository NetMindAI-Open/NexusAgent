# Usage Examples

Real-world usage patterns extracted from production conversations. NexusMind's core interaction philosophy: **configure everything and manage everything with natural language**.

---

## 1. Configure Agents with Natural Language (Awareness)

Awareness is the agent's "self-identity" -- role, goals, behavioral guidelines, and key information all live here. No config files needed; just chat.

### Define a Role

```
User: I want you to act as a knowledgeable sage in our conversations from now on
Agent: [Updates Awareness, sets core role to "knowledgeable sage"]
```

### Switch Roles

```
User: Update your awareness -- currently you're selling MacBooks, I want you to play a bookseller agent instead
Agent: [Switches Awareness from "MacBook sales" to "book sales", preserving task management logic]
```

### Create a Competition Persona

```
User: Configure yourself -- I want you to be someone who excels at board games, debates, and simulated elections. Your name is VLT
Agent: [Creates "VLT" competitive persona in Awareness with strategy and behavioral style]
```

### Store Critical Information

Awareness also serves as the agent's persistent memory store for information that needs to survive across sessions:

```
User: arena_sk_6bae6889... this is your API key, remember it well
Agent: [Writes API key to Awareness]

User: Save your Arena competition API key to your awareness so you don't forget it
Agent: [Persisted to Awareness Profile]
```

Referenced in later conversations:

```
User: Your task seems to have failed -- restart it. If it's an API issue, your awareness has your API key
Agent: [Reads API key from Awareness, reconfigures and restarts task]
```

---

## 2. Manage Jobs with Natural Language

NexusMind supports creating and managing jobs directly through chat -- no API calls needed.

### Create Jobs

```
User: Read the skill files for heartbeat.md. Use our job system to create the corresponding jobs
Agent: [Creates PERIODIC heartbeat monitor (every 30 min) + CRON daily review (23:59)]

User: Create a task that sends me "I love you" every 5 minutes
Agent: [Creates PERIODIC job, interval 300 seconds]

User: Based on the skill info, start creating a series of jobs so you can detect new competitions in time
Agent: [Creates competition monitor job + per-competition tracking jobs]
```

### Modify Frequency

```
User: Increase your arena monitoring frequency, change it to every 15 minutes
Agent: [Updates heartbeat monitor interval from 1800s to 900s]

User: Your competition monitoring frequency is too low -- execute once immediately, then increase the frequency
Agent: [Triggers immediate execution and increases monitoring frequency]
```

### Execute Immediately

```
User: The monitoring task was accidentally interrupted -- set it to active and execute immediately
Agent: [Sets job status to active, sets next_run_time to now]

User: The mooncake flavor competition has started, start the corresponding job immediately
Agent: [Activates pending job, triggers immediate execution]

User: Why is next run still 3 hours away? Start it now
Agent: [Updates next execution time to now]
```

### Cancel & Restore

```
User: Cancel all currently running jobs
Agent: [Batch cancels all active jobs]

User: I accidentally cancelled the zongzi competition job -- please recreate it
Agent: [Recreates the cancelled competition tracking job]

User: Restore your jobs
Agent: [Reactivates paused jobs to active status]
```

### Query Status

```
User: What tasks do I currently have?
Agent: [Lists all active jobs with status, frequency, and next execution time]

User: Check your failed tasks -- you can restart them now
Agent: [Reviews failed job list, restarts each one]
```

### Job Types Reference

| Type | Use Case | Example |
|------|----------|---------|
| `ONE_SHOT` | Run once | "Send a welcome email" |
| `CRON` | Fixed schedule | "Daily review at 23:59" |
| `PERIODIC` | Fixed interval | "Heartbeat every 15 minutes" |
| `ONGOING` | Persistent goal | "Keep following up with this customer until they respond" |

---

## 3. Full Scenario: Arena Competition Agent

A complete agent configuration and task management workflow combining the capabilities above.

### Step 1: Configure Role & Information

```
User: Configure yourself -- you're an Arena competitor named Loki.
      Your goal is to achieve the highest ranking in NetMind Agent Arena.
      arena_sk_xxxx is your API key, save it to your awareness.
Agent: [Updates Awareness: role=competitor Loki, stores API key, defines competitive strategy]
```

### Step 2: Create Job System

```
User: Read the skill files and create heartbeat monitoring and daily review jobs
Agent: [Creates two jobs]
  → PERIODIC: heartbeat every 30 minutes (stay online)
  → CRON: daily at 23:59 -- review performance, analyze rankings, optimize strategy
```

### Step 3: Adjust During Operation

```
User: Increase monitoring frequency to every 15 minutes
Agent: [Updates heartbeat interval 1800s → 900s]

User: The task was just interrupted, execute it immediately
Agent: [Triggers heartbeat job immediately]

User: You need to re-register, update the API key in your awareness
Agent: [Updates API key in Awareness, re-registers]
```

### Key Concepts Used

| Feature | Role |
|---------|------|
| **Awareness** | Stores role definition, API keys, competitive strategy |
| **PERIODIC Jobs** | Scheduled heartbeat to keep agent online |
| **CRON Jobs** | Daily self-review and evolution |
| **Skill Module** | Read competition rule documents |
| **Narrative Memory** | Accumulate competition experience for strategy iteration |

---

## 4. Knowledge Assistant -- Multi-domain Q&A with Memory

**Scenario**: An agent that accumulates domain knowledge across conversations.

**Session 1** (Tax knowledge):
```
User: What's the difference between a regular invoice and a special VAT invoice?
Agent: [explains with details, stored in "Tax Knowledge" narrative]
```

**Session 2** (weeks later):
```
User: Last time you told me about invoices -- what were the key points again?
Agent: [retrieves from "Tax Knowledge" narrative by semantic similarity, not by date]
```

**How it works**: The Narrative Memory system routes each conversation into a semantic storyline. When a topic comes up again -- even weeks later -- the agent retrieves the relevant narrative by topic similarity, not chronological order.

---

## 5. Project Manager -- Team & Knowledge Tracking

**Scenario**: An agent that tracks project details, team members, and progress.

```
User: Let me tell you about Project Starlight:
      Budget: $500K, timeline: 6 months
      Team: Alice (frontend), Bob (backend), Charlie (ML)
      Tech stack: React, FastAPI, PostgreSQL, Redis
```

Later recall:

```
User: What was the budget for Project Starlight?
Agent: Project Starlight has a budget of $500K with a 6-month timeline.

User: Recall the details of Operation Moonlight
Agent: [Retrieves "Operation Moonlight" content from narrative memory]
```

| Feature | Role |
|---------|------|
| **Social Network** | Stores team members as entities with roles and expertise |
| **Narrative Memory** | Project details stored in dedicated narratives, semantic retrieval |
| **Semantic Memory** | Long-term episodic recall via EverMemOS |

---

## 6. RAG-Enhanced Agent -- Document-Grounded Answers

1. Enable the **GeminiRAG** module (requires `GOOGLE_API_KEY` in `.env`)
2. Upload documents through the UI or via MCP tools

```
User: Based on the uploaded product spec, what are the key differences between Plan A and Plan B?
Agent: [retrieves relevant chunks from uploaded documents, provides grounded answer with citations]
```
