---
type: regex
weight: 2
target: { source: file, path: apps/comments/models.py }
pattern: 'ForeignKey\(\s*(["'']articles\.Article["'']|Article\b)[\s\S]*(AUTH_USER_MODEL|get_user_model)|(AUTH_USER_MODEL|get_user_model)[\s\S]*ForeignKey\(\s*(["'']articles\.Article["'']|Article\b)'
---
