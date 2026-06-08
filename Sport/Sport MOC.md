---
type: MOC
domain: Sport
tags: [fitness]
---

# 🏋️ Sport & Training Dashboard

Central hub for fitness, nutrition, and training programs.

## 📈 Active Master Programs
```dataview
table status
from "Sport"
where type = "Program"
sort file.name asc
```

## 🗓️ Recent Training Sessions
```dataview
table activity as "Activity", rpe as "RPE", duration_mins + " min" as "Duration"
from "Sport"
where type = "Session"
sort date desc
limit 10
```

## 📊 Weekly Reviews
```dataview
table week_number as "Week"
from "Sport"
where type = "Review"
sort week_number desc
limit 5
```
