# Local learning memory and Google-grounded research

## Local learning memory

AgentSINC stores a bounded record when a specialist mission completes. The record includes a shortened copy of the task instructions and the final result. It is stored in the local SQLite database in the `agent_memory` table.

For each later mission, the worker retrieves up to three relevant records using a lightweight lexical score over recent mission titles and text. The retrieved snippets are included as **untrusted historical context**; specialists must verify them against the current repository snapshot before relying on them.

The memory store is capped at 500 records. Common credential assignments, bearer tokens and PEM private-key blocks are redacted before storage.

This is persistent local memory / retrieval augmentation. It is **not model training, fine-tuning or a change to Ollama model weights**. It requires no paid AI API and uses only the existing local SQLite database and Ollama model.

## Optional Google Search for the Research Agent

Google's Custom Search JSON API is closed to new customers. AgentSINC therefore uses the Gemini API's Google Search grounding tool as an optional research connector instead of the retired onboarding path.

The connector is disabled by default. It runs only for tasks assigned to the Research Agent and only when both of these are true:

- `AGENTSINC_GOOGLE_SEARCH_ENABLED=true`
- `GEMINI_API_KEY` contains a valid key

The default model is `gemini-2.5-flash`. The connector sends only the Research Agent's mission title and instructions to Google's Gemini API. It does not send the local workspace snapshot, SQLite memory or repository files. Common credential patterns are redacted from the mission prompt before the request is sent. Google grounding source URLs and search queries are attached to the Research Agent's result context.

External research is not performed when the setting is disabled or the key is absent. A failed request is recorded as unavailable; the Research Agent must not claim that it searched the web.

### Enable on Windows

From `E:\AgentSINC\backend`:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set the following values in the local `.env` file:

```dotenv
AGENTSINC_GOOGLE_SEARCH_ENABLED=true
GEMINI_API_KEY=your_key_from_google_ai_studio
AGENTSINC_GOOGLE_SEARCH_MODEL=gemini-2.5-flash
```

Keep the key out of Git, screenshots, mission text and support messages. The `.env` file is local configuration and must not be committed. Restart both the API and the worker after changing it. The Studio Settings panel displays whether Google Search is enabled.

Google's published Gemini API pricing currently lists up to 500 Google Search-grounded requests per day at no charge for Gemini 2.5 Flash and Flash-Lite standard free-tier access. A single grounded prompt may result in multiple search queries, and limits can change. The current model catalogue also warns that Gemini 2.5 access is limited for projects that have not actively used those models before; new projects are directed to newer Gemini 3.x models. Google does not list Search grounding as available on the Gemini 3.x free tier in the current pricing table. This connector therefore does not automatically fall forward to a different model or paid tier if 2.5 access is unavailable. Verify the current account's model access and pricing before enabling it: https://ai.google.dev/gemini-api/docs/pricing and https://ai.google.dev/gemini-api/docs/models.

Google's pricing page also states that free-tier content may be used to improve Google products. Do not submit confidential company data, personal data or secrets through this optional connector. The free quota is not a guarantee that every account/region can use the model or that usage above the free allowance will remain free.

Google Search grounding is an external service. Mission prompts sent to it leave the local machine; do not include confidential business information or personal data in Research Agent instructions unless that external processing is acceptable.

## Honest capability boundaries

- Research Agent can use Google-grounded search only when explicitly enabled. The other agents remain local-only.
- Specialists receive read-only repository context. They cannot execute shell commands, modify project files, run tests, deploy software or open pull requests.
- The 3D desk panels reflect real API task state; they do not prove that a specialist performed an external action.
- Actual model-weight training, isolated code execution, approved file changes and autonomous pull-request creation are separate future capabilities.
