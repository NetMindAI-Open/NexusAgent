/**
 * Chat store
 * Manages chat messages, steps, and conversation history
 */

import { create } from 'zustand';
import type {
  ChatMessage,
  Step,
  ConversationRound,
  RuntimeMessage,
  ProgressMessage,
  AgentTextDelta,
  AgentThinking,
  AgentToolCall,
} from '@/types';
import { generateId } from '@/lib/utils';

// Total AgentRuntime pipeline steps (only counting 6 major steps: 0, 1, 2, 3, 4, 5)
const TOTAL_PIPELINE_STEPS = 6;

interface ChatState {
  // Current conversation
  messages: ChatMessage[];
  currentSteps: Step[];
  currentThinking: string;
  currentToolCalls: AgentToolCall[];
  totalSteps: number;  // Total pipeline steps

  // History
  history: ConversationRound[];

  // Status
  isStreaming: boolean;
  currentAssistantMessage: string;  // LLM raw output (internal thinking)

  // Computed: user-visible response content (extracted from send_message_to_user_directly tool call)
  getUserVisibleResponse: () => string | null;

  // Actions
  addUserMessage: (content: string) => string;
  startStreaming: () => void;
  stopStreaming: () => void;
  processMessage: (message: RuntimeMessage) => void;
  saveToHistory: () => void;
  clearCurrent: () => void;
  clearAll: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  messages: [],
  currentSteps: [],
  currentThinking: '',
  currentToolCalls: [],
  totalSteps: TOTAL_PIPELINE_STEPS,
  history: [],
  isStreaming: false,
  currentAssistantMessage: '',

  // Computed: get user-visible response content
  // Only the content from send_message_to_user_directly tool call is visible to the user
  // Note: Claude Agent SDK tool name format is mcp__chat_module__send_message_to_user_directly
  getUserVisibleResponse: () => {
    const state = get();
    const makeResponseCall = state.currentToolCalls.find(
      (tool) => tool.tool_name.endsWith('send_message_to_user_directly')
    );
    if (makeResponseCall && makeResponseCall.tool_input?.content) {
      return makeResponseCall.tool_input.content as string;
    }
    return null;
  },

  // Add user message
  addUserMessage: (content) => {
    const id = generateId();
    const message: ChatMessage = {
      id,
      role: 'user',
      content,
      timestamp: Date.now(),
    };
    set((state) => ({
      messages: [...state.messages, message],
    }));
    return id;
  },

  // Start streaming
  startStreaming: () => {
    set({
      isStreaming: true,
      currentAssistantMessage: '',
      currentSteps: [],
      currentThinking: '',
      currentToolCalls: [],
    });
  },

  // Stop streaming and save to history
  stopStreaming: () => {
    const state = get();
    // Prevent duplicate calls: return early if not in streaming state
    if (!state.isStreaming) {
      return;
    }

    // Core logic: extract user-visible response content from send_message_to_user_directly tool call
    // All LLM output from the agent is internal thinking; only send_message_to_user_directly content is shown to the user
    // Note: Claude Agent SDK tool name format is mcp__chat_module__send_message_to_user_directly
    const makeResponseCall = state.currentToolCalls.find(
      (tool) => tool.tool_name.endsWith('send_message_to_user_directly')
    );

    // Determine content to display to the user
    let displayContent: string;
    if (makeResponseCall && makeResponseCall.tool_input?.content) {
      // send_message_to_user_directly was called, extract the content parameter
      displayContent = makeResponseCall.tool_input.content as string;
    } else {
      // send_message_to_user_directly was not called, show default message
      displayContent = '(Agent decided no response needed)';
    }

    const userMessage = state.messages.find((m) => m.role === 'user');
    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: displayContent,
      timestamp: Date.now(),
      // Save LLM raw output as thinking (internal reasoning process)
      thinking: state.currentThinking || state.currentAssistantMessage || undefined,
      toolCalls: state.currentToolCalls.length > 0 ? [...state.currentToolCalls] : undefined,
    };

    // Before saving, mark all steps still in RUNNING state as COMPLETED
    // This fixes the issue where certain tool calls (e.g., job_retrieval_by_id, search_social_network)
    // still show a spinner after the pipeline completes
    const completedSteps = state.currentSteps.map((step) => {
      if (step.status === 'running') {
        return {
          ...step,
          status: 'completed' as const,
          description: step.description.replace('Executing...', '✓ Done').replace('Running...', '✓ Done'),
        };
      }
      return step;
    });

    // Save to history if we have both messages
    let newHistory = state.history;
    if (userMessage) {
      const round: ConversationRound = {
        id: generateId(),
        userMessage,
        assistantMessage,
        steps: completedSteps,
        timestamp: Date.now(),
      };
      newHistory = [round, ...state.history];
    }

    set({
      messages: [...state.messages, assistantMessage],
      currentSteps: completedSteps,  // Also update current step state
      history: newHistory,
      isStreaming: false,
    });
  },

  // Process incoming message
  processMessage: (message) => {
    switch (message.type) {
      case 'progress': {
        const progress = message as ProgressMessage;
        set((state) => {
          // Find existing step or create new
          const existingIndex = state.currentSteps.findIndex(
            (s) => s.step === progress.step
          );
          const step: Step = {
            id: progress.step,
            step: progress.step,
            title: progress.title,
            description: progress.description,
            status: progress.status,
            substeps: progress.substeps,
            details: progress.details,
            timestamp: progress.timestamp,
          };

          // Extract tool call info from progress.details
          // The backend sends tool calls as progress messages with tool_name and arguments in details
          let newToolCalls = state.currentToolCalls;
          if (progress.details?.tool_name && progress.details?.arguments) {
            const toolCall: AgentToolCall = {
              type: 'tool_call',
              timestamp: progress.timestamp,
              tool_name: progress.details.tool_name as string,
              tool_input: progress.details.arguments as Record<string, unknown>,
            };
            // Deduplicate by tool_name + timestamp (same tool at same timestamp is a duplicate)
            const exists = state.currentToolCalls.some(
              (t) => t.tool_name === toolCall.tool_name && t.timestamp === toolCall.timestamp
            );
            if (!exists) {
              newToolCalls = [...state.currentToolCalls, toolCall];
            }
          }

          if (existingIndex >= 0) {
            const newSteps = [...state.currentSteps];
            newSteps[existingIndex] = step;
            return { currentSteps: newSteps, currentToolCalls: newToolCalls };
          }
          return { currentSteps: [...state.currentSteps, step], currentToolCalls: newToolCalls };
        });
        break;
      }

      case 'agent_response': {
        const delta = message as AgentTextDelta;
        set((state) => ({
          currentAssistantMessage: state.currentAssistantMessage + delta.delta,
        }));
        break;
      }

      case 'agent_thinking': {
        const thinking = message as AgentThinking;
        set((state) => ({
          currentThinking: state.currentThinking + thinking.thinking_content,
        }));
        break;
      }

      case 'tool_call': {
        const toolCall = message as AgentToolCall;
        set((state) => ({
          currentToolCalls: [...state.currentToolCalls, toolCall],
        }));
        break;
      }

      case 'error': {
        // Handle error - could show in UI
        console.error('Runtime error:', message);
        break;
      }

      case 'complete': {
        get().stopStreaming();
        break;
      }
    }
  },

  // Save current conversation to history
  saveToHistory: () => {
    const state = get();
    const userMessage = state.messages.find((m) => m.role === 'user');
    const assistantMessage = state.messages.find((m) => m.role === 'assistant');

    if (userMessage && assistantMessage) {
      const round: ConversationRound = {
        id: generateId(),
        userMessage,
        assistantMessage,
        steps: state.currentSteps,
        timestamp: Date.now(),
      };
      set((state) => ({
        history: [round, ...state.history],
      }));
    }
  },

  // Clear current conversation
  clearCurrent: () => {
    set({
      messages: [],
      currentSteps: [],
      currentThinking: '',
      currentToolCalls: [],
      currentAssistantMessage: '',
      isStreaming: false,
    });
  },

  // Clear everything
  clearAll: () => {
    set({
      messages: [],
      currentSteps: [],
      currentThinking: '',
      currentToolCalls: [],
      history: [],
      currentAssistantMessage: '',
      isStreaming: false,
    });
  },
}));
