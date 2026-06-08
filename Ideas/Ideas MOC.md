---
type: MOC
domain: Ideas
tags: [product-management, personal-growth, startups]
---

# 💡 Ideas Incubator MOC

Welcome to the greenhouse. Ideas start as seeds and either sprout into projects or get archived.

## 🌱 Active Ideas (Seeds & Sprouts)
```dataview
table status, file.mtime as "Last Updated"
from "Ideas"
where status != "Promoted" and status != "Archived" and file.name != "Ideas MOC"
sort file.mtime desc
```

## 🚀 Promoted to Projects
```dataview
list
from "Ideas"
where status = "Promoted"
sort file.mtime desc
```
