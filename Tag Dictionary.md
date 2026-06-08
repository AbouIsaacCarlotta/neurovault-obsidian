# 📚 Master Tag Dictionary

This file acts as the ultimate source of truth for the `tag_audit.py` script. Any tag found in the vault that is not on this approved list will be flagged or automatically mapped to one of these.

## 📏 Tagging Best Practices
Before looking at the clusters, here are the absolute rules for tag syntax that the script will enforce:
1. **Always lowercase**: `ai`, never `AI` or `Ai`.
2. **Kebab-case for spaces**: Always use a dash `-` instead of spaces or camelCase. `product-management`, never `product management` or `productManagement`.
3. **No format tags**: Since you use `type: Article` or `type: Transcript` in your YAML, tags like `podcast`, `transcript`, or `pdf` are banned. Tags are exclusively for **topics**.
4. **Max 5 tags per note**: To force you (and the LLM) to pick only the most critical concepts.

## 🐣 Tag Incubation & Graduation Process (The Rule of 3)
A dictionary must be a living document. You are absolutely allowed to research new domains (like `ceramics` or `nutrition`). 
Here is how new tags enter the dictionary:
1. **Provisional Creation**: You (or the LLM) can create a new tag at any time, as long as it follows the syntax rules (lowercase, kebab-case).
2. **Incubation**: The script will ignore unknown tags if they are only used once or twice. They remain "provisional".
3. **Graduation (The Rule of 3)**: When the `tag_audit.py` script runs, it counts how many times a provisional tag is used. If you have tagged **3 distinct notes** with `ceramics`, the script considers it a permanent interest. It will automatically "graduate" the tag and append it to this Master Dictionary file. 

---

## 🎯 The 30 Core Clusters

### 🤖 Artificial Intelligence
- `ai` *(Maps: AI, artificial-intelligence, genai)*
- `agentic-ai` *(Maps: ai-agents, agents, agent-native, autonomous-agents)*
- `ai-models` *(Maps: llms, llm, local-llm, claude, openai, gemini, huggingface)*
- `ai-infrastructure` *(Maps: ai-efficiency, llmops, ai-database, ai-inference)*
- `prompt-engineering`

### 🏗️ Product & Design
- `product-management` *(Maps: product-strategy, product-features, prd, specs)*
- `ux-design` *(Maps: ux, ui-ux, interface, design-patterns, design-thinking)*
- `product-led-growth`

### 💼 Business, Startups & Strategy
- `startups` *(Maps: founders, tech-startups, ai-startups, lean-startup, indie-hacking, yc)*
- `venture-capital` *(Maps: angel-investing, investment, accelerator)*
- `business-strategy` *(Maps: strategy, go-to-market, growth-strategy, capability-mapping)*
- `enterprise-software` *(Maps: enterprise-ai, b2b, b2b-software, saas, workday)*
- `marketing` *(Maps: sales, storytelling, viral-launch, seo)*

### 💻 Engineering & Data
- `software-engineering` *(Maps: engineering, software-development, coding, software-architecture)*
- `devops` *(Maps: infrastructure, cloud, platform-engineering, serverless)*
- `data-engineering` *(Maps: database, graph-database, neo4j, knowledge-graphs)*
- `security` *(Maps: compliance)*

### 🧠 Leadership & Personal
- `leadership` *(Maps: management, engineering-management, it-management, ceo, executive)*
- `personal-growth` *(Maps: career, personal-development, mental-models)*
- `productivity` *(Maps: work-log)*
- `personal-brand`

### 💰 Finance & Operations
- `fintech` *(Maps: finance, banking)*
- `crypto` *(Maps: stablecoins, stablecoin, blockchain)*
- `operations` *(Maps: supply-chain, governance)*

### 🌐 Industry Verticals
- `healthcare`
- `edtech`

---
*Note: When `tag_audit.py` runs, it will read this file. If it sees `ai-agents` on a file, it will look at this list, see that it maps to `agentic-ai`, and automatically rewrite the YAML in the file.*


## 🆕 Newly Graduated Tags
- `movies`
- `health`
- `fitness`
- `feedback`
- `tech`
- `okrs`
- `decisive`
- `meeting`
- `python`
- `pitch`
- `communication`
- `ai-coding`
- `developer-tools`
- `automation`
- `linkedin`
- `anthropic`
- `business-architecture`
- `enterprise-architecture`
