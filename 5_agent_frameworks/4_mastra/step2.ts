/**
 * Step 2: Run it.
 *
 * Send a message, await the reply, and print the result's .text. With no tools yet
 * there is nothing to loop over, so the agent just answers. This is still only an
 * LLM call. Run it with: npm run step2
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

const reply = await agent.generate("Say hello in Spanish.");
console.log(reply.text);

process.exit(0); // Mastra keeps its model connection pool open, so exit once the work is done
