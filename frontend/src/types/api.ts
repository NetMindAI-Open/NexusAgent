/**
 * API response type definitions
 */

// Job types
export type JobStatus = 'pending' | 'active' | 'running' | 'paused' | 'completed' | 'failed' | 'blocked' | 'cancelled';
export type JobType = 'one_off' | 'scheduled' | 'ongoing';

export interface TriggerConfig {
  trigger_type?: string;
  interval_seconds?: number;
  cron_expression?: string;
  timezone?: string;
  [key: string]: unknown;
}

export interface Job {
  job_id: string;
  agent_id: string;
  user_id: string;
  job_type: string;
  title: string;
  description?: string;
  status: string;
  payload?: string;
  trigger_config?: TriggerConfig;
  process?: string[];
  next_run_time?: string;
  last_run_time?: string;
  last_error?: string;
  notification_method?: string;
  created_at?: string;
  updated_at?: string;
  // Dependencies (fetched from module_instances table)
  instance_id?: string;
  depends_on?: string[];
  // New fields (Feature 2.2, 3.1)
  related_entity_id?: string;      // Target user ID (used as the principal identity during Job execution)
  narrative_id?: string;           // Associated Narrative ID (conversation context)
}

export interface JobListResponse {
  success: boolean;
  jobs: Job[];
  count: number;
  error?: string;
}

export interface JobDetailResponse {
  success: boolean;
  job?: Job;
  error?: string;
}

export interface CancelJobResponse {
  success: boolean;
  job_id?: string;
  previous_status?: string;
  error?: string;
}

// Inbox types (User Inbox)
export interface MessageSource {
  type?: string;
  id?: string;
}

export interface InboxMessage {
  message_id: string;
  user_id: string;
  message_type: string;
  title: string;
  content: string;
  source?: MessageSource;
  event_id?: string;
  is_read: boolean;
  created_at?: string;
}

export interface InboxListResponse {
  success: boolean;
  messages: InboxMessage[];
  count: number;
  unread_count: number;
  error?: string;
}

export interface MarkReadResponse {
  success: boolean;
  marked_count: number;
  error?: string;
}

// Agent Inbox types
export type AgentMessageSourceType = 'user' | 'agent' | 'system';

export interface AgentInboxMessage {
  message_id: string;
  agent_id: string;
  source_type: AgentMessageSourceType;
  source_id: string;
  content: string;
  if_response: boolean;
  narrative_id?: string;
  event_id?: string;
  created_at?: string;
}

export interface AgentInboxListResponse {
  success: boolean;
  messages: AgentInboxMessage[];
  count: number;
  unresponded_count: number;
  error?: string;
}

export interface MarkRespondedResponse {
  success: boolean;
  marked_count: number;
  error?: string;
}

// Awareness types
export interface AwarenessResponse {
  success: boolean;
  awareness?: string;
  create_time?: string;
  update_time?: string;
  error?: string;
}

// Clear history types
export interface ClearHistoryResponse {
  success: boolean;
  narrative_ids_deleted: string[];
  narratives_count: number;
  events_count: number;
  error?: string;
}

// Social Network types
export interface SocialNetworkEntity {
  entity_id: string;
  entity_name?: string;
  entity_description?: string;
  entity_type: string;
  identity_info: Record<string, unknown>;
  contact_info: Record<string, unknown>;
  tags: string[];
  relationship_strength: number;
  interaction_count: number;
  last_interaction_time?: string;
  // New fields (Feature 2.2, 2.3)
  persona?: string;                // Communication style/characteristics
  related_job_ids?: string[];      // Associated Job IDs
  expertise_domains?: string[];    // Expertise domains
}

export interface SocialNetworkResponse {
  success: boolean;
  entity?: SocialNetworkEntity;
  error?: string;
}

export interface SocialNetworkListResponse {
  success: boolean;
  entities: SocialNetworkEntity[];
  count: number;
  error?: string;
}

// Semantic search response
export interface SocialNetworkSearchResponse {
  success: boolean;
  entities: Array<SocialNetworkEntity & { similarity_score?: number }>;
  count: number;
  search_type: 'keyword' | 'semantic';
  error?: string;
}

// Chat History types
export interface EventLogEntry {
  timestamp: string;
  type: string;
  content: unknown;
}

// Simple Chat History types (for displaying recent interactions)
export interface SimpleChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  narrative_id?: string;
}

export interface SimpleChatHistoryResponse {
  success: boolean;
  messages: SimpleChatMessage[];
  total_count: number;
  error?: string;
}

export interface ChatHistoryEvent {
  event_id: string;
  narrative_id?: string;
  narrative_name?: string;
  trigger: string;
  trigger_source: string;
  user_id?: string;
  final_output: string;
  created_at: string;
  event_log: EventLogEntry[];
}

// Module Instance info for displaying in Narrative
export interface InstanceInfo {
  instance_id: string;
  module_class: string;
  description: string;
  status: string;
  dependencies: string[];
  config: Record<string, unknown>;
  created_at?: string;
  user_id?: string;  // Used to filter events by user_id
}

export interface ChatHistoryNarrative {
  narrative_id: string;
  name: string;
  description: string;
  current_summary: string;
  actors: Array<{ id: string; type: string }>;
  created_at: string;
  updated_at: string;
  instances: InstanceInfo[];  // Associated Module Instances
}

export interface ChatHistoryResponse {
  success: boolean;
  narratives: ChatHistoryNarrative[];
  events: ChatHistoryEvent[];
  narrative_count: number;
  event_count: number;
  error?: string;
}

// Create Agent types
export interface CreateAgentRequest {
  agent_name?: string;
  agent_description?: string;
  created_by: string;
}

export interface AgentInfo {
  agent_id: string;
  name?: string;
  description?: string;
  status?: string;
  created_at?: string;
}

export interface CreateAgentResponse {
  success: boolean;
  agent?: AgentInfo;
  error?: string;
}

export interface UpdateAgentRequest {
  agent_name?: string;
  agent_description?: string;
}

export interface UpdateAgentResponse {
  success: boolean;
  agent?: AgentInfo;
  error?: string;
}

export interface DeleteAgentResponse {
  success: boolean;
  agent_id?: string;
  deleted_counts?: Record<string, number>;
  error?: string;
}

// File Management types
export interface FileInfo {
  filename: string;
  size: number;
  modified_at: string;
}

export interface FileListResponse {
  success: boolean;
  files: FileInfo[];
  workspace_path: string;
  error?: string;
}

export interface FileUploadResponse {
  success: boolean;
  filename?: string;
  size?: number;
  workspace_path?: string;
  error?: string;
}

export interface FileDeleteResponse {
  success: boolean;
  filename?: string;
  error?: string;
}

// MCP Management types
export interface MCPInfo {
  mcp_id: string;
  agent_id: string;
  user_id: string;
  name: string;
  url: string;
  description?: string;
  is_enabled: boolean;
  connection_status?: 'connected' | 'failed' | 'unknown' | null;
  last_check_time?: string;
  last_error?: string;
  created_at?: string;
  updated_at?: string;
}

export interface MCPListResponse {
  success: boolean;
  mcps: MCPInfo[];
  count: number;
  error?: string;
}

export interface MCPCreateRequest {
  name: string;
  url: string;
  description?: string;
  is_enabled?: boolean;
}

export interface MCPUpdateRequest {
  name?: string;
  url?: string;
  description?: string;
  is_enabled?: boolean;
}

export interface MCPResponse {
  success: boolean;
  mcp?: MCPInfo;
  error?: string;
}

export interface MCPValidateResponse {
  success: boolean;
  mcp_id: string;
  connected: boolean;
  error?: string;
}

export interface MCPValidateAllResponse {
  success: boolean;
  results: MCPValidateResponse[];
  total: number;
  connected: number;
  failed: number;
  error?: string;
}

// RAG File Management types
export type RAGFileStatus = 'pending' | 'uploading' | 'completed' | 'failed';

export interface RAGFileInfo {
  filename: string;
  size: number;
  modified_at: string;
  upload_status: RAGFileStatus;
  error_message?: string;
}

export interface RAGFileListResponse {
  success: boolean;
  files: RAGFileInfo[];
  total_count: number;
  completed_count: number;
  pending_count: number;
  error?: string;
}

export interface RAGFileUploadResponse {
  success: boolean;
  filename?: string;
  size?: number;
  upload_status?: string;
  error?: string;
}

export interface RAGFileDeleteResponse {
  success: boolean;
  filename?: string;
  error?: string;
}
