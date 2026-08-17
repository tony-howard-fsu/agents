/**
 * Step 1: Create the agent.
 *
 * In Mastra an agent is an Agent: a name, instructions (its system prompt), and a
 * model. The model is the routing string "openai/gpt-5.4-mini", resolved through the
 * Vercel AI SDK, which picks OpenAI and reads OPENAI_API_KEY from the environment.
 * Nothing runs yet; we just build it. Run it with: npm run step1
 */

import "./env.ts";
import { Agent } from "@mastra/core/agent";
import { createOpenAI } from "@ai-sdk/openai";
import { resolveWorkerModel } from "./providers.ts";

const { modelId, baseURL, apiKey } = resolveWorkerModel("deepseek/deepseek-v4-flash");
const provider = createOpenAI({
  ...(baseURL ? { baseURL } : {}),
  apiKey,
});

const agent = new Agent({
  id: "assistant",
  name: "Assistant",
  instructions: "You are a concise, friendly assistant. Reply in a single short sentence.",
  //model: "openai/gpt-5.4-mini",
  // provider(...) defaults to OpenAI's stateful Responses API (/responses), which DeepSeek
  // doesn't implement; provider.chat(...) targets the classic /chat/completions endpoint instead.
  model: provider.chat(modelId),
});

console.log(`Created agent: ${agent.name}`);
