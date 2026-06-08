---
type: MOC
domain: Projects
tags: [projects, product-management, product-led-growth]
---

# 🚀 Projects MOC

Central hub for all ongoing and closed projects. 

## 🟢 Ongoing Projects
```dataview
table file.ctime as "Created"
from "Projects/Ongoing"
sort file.mtime desc
```

## 🔴 Closed Projects
```dataview
list
from "Projects/Closed"
sort file.mtime desc
```
