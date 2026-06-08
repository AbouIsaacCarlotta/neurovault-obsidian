---
type: Dashboard
status: Active
tags: [productivity, personal-growth, project-management, fitness]
---

# 🧠 My Second Brain Dashboard

Welcome to your central hub. From here, you can navigate to all major areas of your knowledge graph.

## 🗺️ Maps of Content (MOCs)
- [[Knowledge MOC]] - All articles, concepts, and learnings.
- [[Projects MOC]] - Active and closed projects.
- [[Ideas MOC]] - The incubator for seeds and sprouting concepts.
- [[Work MOC]] - Professional development and execution.
- [[Personal MOC]] - Life domains, therapy, and journaling.
- [[Culture MOC]] - Media trackers (Films, Books, Music).
- [[Task Dashboard]] - Universal task aggregator and Inbox.
- [[Sport MOC]] - Training logs and nutrition.

## 📊 Overview
```dataview
table status, domain
from "Projects"
where status = "Ongoing"
sort file.mtime desc
limit 5
```
