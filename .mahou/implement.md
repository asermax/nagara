# Implement

Task tracker: **Linear**, workspace `asermax`, team Asermax (key `ASE`), project **nagara**.

Reached through the `linear-server` MCP tools: `save_issue` creates an issue (team, title, description, project, milestone, labels, priority) and updates one (`id` plus `title`, `description`, `state`, `labels`); `list_issues` reads them (filter by `project`); `save_comment` comments on an issue.

States a task moves through: `Backlog` (the default) → `Todo` (about to be worked) → `In Progress` (started) → `Done` (implemented, tested and committed). A task a settled design retires is set `Canceled` with a comment naming the note that supersedes it, never deleted silently.

Priorities: 2 High, 3 Medium, 4 Low. Labels: `Bug`, `Feature`, `Improvement`, `Spike`. A milestone is a feature; an issue is one task under it, or a loose task with no milestone.
