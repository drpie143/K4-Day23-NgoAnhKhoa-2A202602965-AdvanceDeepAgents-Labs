# Survey of LLM Agents and Tool Use

## Introduction
Large Language Model (LLM) agents have increasingly become integral in many technological fields. Their adaptability in handling diverse tasks is primarily attributed to their tool usage. This report provides a comprehensive overview of current capabilities, tool integration strategies, and the evolution of LLM agents in recent years.

## Capabilities of LLM Agents

LLM agents today possess a wide array of capabilities. These can vary significantly based on the installed skill sets. However, challenges arise when these skills conflict, particularly when co-installed in coding environments, leading to the potential loss of core capabilities [1]. New benchmarks like SWE-Journey address these issues by providing more realistic measures for evaluating agent performance under long-term, interactive tasks [2]. Moreover, evolving functional repertoires have enabled continual learning without the need for heavy parameter updates, enhancing model efficiency [3]. A live-commerce environment like StoreBench further pushes LLMs to showcase planning and operational skills in dynamic scenarios [4]. Coordination among agents is also critical to avoid conflict and ensure collaborative success, as demonstrated by scheduling approaches proposed in recent studies [5].

## Tool Use and Integration Strategies

Tool integration is a fundamental aspect of LLM agent efficacy. Recent strategies discuss methods like ToolScope, which merges overlapping tools and uses context-aware filtering to improve selection accuracy, enhancing tool effectiveness by up to 38.6% [6]. The transition from single-tool usage to multi-tool orchestration has highlighted the need for cognitive architectures to streamline tool integration [7]. Innovations like agent-native reusable tool primitives and centralized control systems further support dynamic tool invocation and execution [8]. Within multi-agent frameworks, using tool cards allows for seamless integration and replacement of diverse tools [9]. Experience networks built around semantic and dependency awareness also contribute to optimized multi-tool selection [10].

## Evolution and Trends in LLM Agent Research

Recent developments in LLM agent research emphasize frameworks that lower entry barriers for agent design and evaluation. Platforms such as FROAV and AgentLite simplify the development and testing of agent architectures [11][12]. Methods focusing on tool learning through simulated trial and error have shown to improve results beyond existing models like GPT-4 [13]. Moreover, benchmarks like ACEBench and ToolTalk provide crucial insights into tool effectiveness in practical settings, addressing API interaction complexities [14][15]. Finally, novel modular frameworks such as language hooks enable enhancements in reasoning without needing specific task prompts [16]. These trends suggest a promising horizon for advancing LLM agent capabilities and applicability.

## Conclusion

The survey reveals significant strides in the versatility and integration strategies of LLM agents. As research continues to propel these technologies, understanding evolving methods and benchmarks will be critical for future deployments. Continuous exploration of coordination strategies and performance benchmarks will ensure the robust development of these sophisticated systems.

---

## References
[1] One Skill Too Many: How Co-Installed Skills Conflict in Coding Agents. arxiv. https://arxiv.org/abs/2610.11647 (2026-10-08)
[2] SWE-Journey: Towards More Realistic Evaluation of Coding Assistants through Long-Horizon, Multi-Turn Interaction. arxiv. https://arxiv.org/abs/2610.11559 (2026-10-08)
[3] From a Prompt to Repertoires: Evolving Functional REpertoires Enable LLM Continual Learning. arxiv. https://arxiv.org/abs/2610.11373 (2026-10-08)
[4] StoreBench: A Live-Commerce Environment for Evaluating and Training Autonomous Operator Agents. arxiv. https://arxiv.org/abs/2610.10942 (2026-10-07)
[5] Verifying Coordination in Parallel Coding Agents: NP-Bench and a Scheduling Planner. arxiv. https://arxiv.org/abs/2610.07261 (2026-10-05)
[6] ToolScope: Enhancing LLM Agent Tool Use through Tool Merging and Context-Aware Filtering. web. https://aclanthology.org/2026.acl-long.1573.pdf (N/A)
[7] The Evolution of Tool Use in LLM Agents: From Single-Tool Call to Multi-Tool Orchestration. web. https://arxiv.org/html/2603.22862v1 (N/A)
[8] Harness Engineering in LLM Tool Use via Agent-Native Reusable Tool Primitives. web. https://arxiv.org/abs/2609.01736 (2026-09-01)
[9] OctoTools: A Multi-Agent Framework with Extensible Tools for Complex Reasoning. web. https://aclanthology.org/2026.acl-long.1.pdf (N/A)
[10] ToolExpNet: Optimizing Multi-Tool Selection in LLMs with Similarity and Dependency-Aware Experience Networks. web. https://aclanthology.org/2025.findings-acl.811.pdf (N/A)
[11] FROAV: A Framework for RAG Observation and Agent Verification -- Lowering the Barrier to LLM Agent Research. hf-search. https://huggingface.co/papers/2601.07504 (2026-01-12)
[12] AgentLite: A Lightweight Library for Building and Advancing Task-Oriented LLM Agent System. hf-search. https://huggingface.co/papers/2402.15538 (2024-02-23)
[13] LLMs in the Imaginarium: Tool Learning through Simulated Trial and Error. hf-search. https://huggingface.co/papers/2403.04746 (2024-03-07)
[14] ACEBench: Who Wins the Match Point in Tool Usage?. hf-search. https://huggingface.co/papers/2501.12851 (2025-01-22)
[15] ToolTalk: Evaluating Tool-Usage in a Conversational Setting. hf-search. https://huggingface.co/papers/2311.10775 (2023-11-15)
[16] Language hooks: a modular framework for augmenting LLM reasoning that decouples tool usage from the model and its prompt. hf-search. https://huggingface.co/papers/2412.05967 (2024-12-08)
