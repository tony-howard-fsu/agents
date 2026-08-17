/**
 * Resolves a WORKER_MODEL "provider/model-id" string into what @ai-sdk/openai's
 * createOpenAI needs: a bare model id, a baseURL, and an apiKey. The TypeScript twin
 * of worker_llm.py's PROVIDERS table (2_strands_pydantic/, 3_maf_agno/) — same idea,
 * one place to add a provider so worker.ts picks it up without a code change.
 */

type ProviderEntry = { baseURL?: string; apiKeyEnv?: string };

const PROVIDERS: Record<string, ProviderEntry> = {
  deepseek: { baseURL: "https://api.deepseek.com", apiKeyEnv: "DEEPSEEK_API_KEY" },
  openai: { apiKeyEnv: "OPENAI_API_KEY" }, // no baseURL: let the client use OpenAI's own default
  groq: { baseURL: "https://api.groq.com/openai/v1", apiKeyEnv: "GROQ_API_KEY" },
  ollama: { baseURL: process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1" },
};

export function resolveWorkerModel(modelSpec: string): { modelId: string; baseURL?: string; apiKey: string } {
  const slash = modelSpec.indexOf("/");
  if (slash < 0) {
    throw new Error(`WORKER_MODEL '${modelSpec}' is missing a provider prefix, e.g. 'deepseek/${modelSpec}'.`);
  }
  const provider = modelSpec.slice(0, slash);
  const modelId = modelSpec.slice(slash + 1);
  const entry = PROVIDERS[provider];
  if (!entry) {
    throw new Error(`Unknown provider '${provider}' in WORKER_MODEL '${modelSpec}'. Known: ${Object.keys(PROVIDERS).join(", ")}.`);
  }
  if (!entry.apiKeyEnv) {
    return { modelId, baseURL: entry.baseURL, apiKey: "not-needed" };
  }
  const apiKey = process.env[entry.apiKeyEnv];
  if (!apiKey) {
    // Fail fast and clearly, matching worker_llm.py's bare os.environ[...] KeyError —
    // otherwise this sails through as apiKey: "" and only surfaces later as an opaque
    // 401 from deep inside a network call.
    throw new Error(`Missing required env var '${entry.apiKeyEnv}' for provider '${provider}' (WORKER_MODEL='${modelSpec}').`);
  }
  return { modelId, baseURL: entry.baseURL, apiKey };
}
