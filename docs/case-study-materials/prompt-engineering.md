* **Prompt engineering basics**: Use large language models (LLMs) via the API to generate text from a prompt. Outputs can include multiple items—tools, reasoning data, and text—so don’t assume the first array element contains your desired response. Official SDKs offer a convenient `output_text` property that concatenates text outputs.

* **Model selection**:

  * *Reasoning models* generate an internal chain of thought and excel at complex, multi-step tasks but are slower and costlier.
  * *GPT models* are faster and cheaper but need explicit instructions.
  * *Model size* (nano/mini/large) trades off speed, cost and intelligence; larger models handle broader tasks better.
  * For general-purpose work, `gpt-4.1` provides a balance of quality and cost.

* **Prompt engineering strategies**:

  * Write clear instructions; the process is non-deterministic, so expect to iterate.
  * Pin your app to a specific model snapshot (e.g., `gpt-4.1-2025-04-14`) for consistent outputs.
  * Build evaluations to measure prompt performance over time.

* **Using message roles and instructions**:

  * Use the `instructions` parameter for high-level guidance; it overrides the prompt text.
  * Alternatively, supply an array of messages with roles: `developer` (system-level rules), `user` (end-user query), and `assistant` (model output). Developer messages take precedence over user messages.
  * Conversation state persists across turns unless you override it; the `instructions` parameter applies only to the current call.

* **Reusable prompts**:

  * Create prompt templates in the OpenAI dashboard with placeholders (e.g., `{{customer_name}}`).
  * Reference these prompts via `prompt.id` and pass variables in your API call.
  * Variables can be strings or file inputs (e.g., PDFs) for retrieval‑augmented generation.

* **Formatting prompts with Markdown and XML**:

  * Use Markdown headers and lists to organize identity, instructions, examples, and context.
  * XML tags clearly delineate user queries, assistant responses and metadata.
  * Place frequently reused instructions at the start of your prompt to benefit from prompt caching.

* **Few-shot learning**:

  * Include a handful of labeled examples in your developer message to teach the model to perform a classification or pattern-matching task without fine-tuning.
  * Examples should cover a range of possible inputs and desired outputs.

* **Provide relevant context (RAG)**:

  * Include proprietary or external data in your prompt when needed, often by retrieving documents (e.g., via vector search or file search).
  * Keep in mind each model’s context window (maximum token limit); newer GPT‑4.1 models can handle up to a million tokens.

* **GPT‑5 prompting tips**:

  * For coding tasks, define the agent’s role, show tool usage examples, and instruct the model to test and validate its own code.
  * For front-end tasks, specify UI/UX standards (typography, colors, interactions), structure, reusable components, and ask the model to scaffold projects and document its work.
  * In agentic scenarios, require the model to plan, explain its tool choices and track progress until the user confirms completion.

* **Reasoning models vs GPT models**: Treat reasoning models like senior coworkers who need only high-level goals, while GPT models are like junior coworkers who require detailed instructions.

* **Next steps and resources**: Experiment with prompts in the Playground, explore structured outputs for JSON, and consult the full API reference. The OpenAI Cookbook contains additional examples and links to prompting tools, guides, videos and research papers.

