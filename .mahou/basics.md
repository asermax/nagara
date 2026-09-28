# Basics

- Subagents run through `herdr-subagents:delegate`, not the Agent tool. Each one is a herdr tab. When a skill names a mahou agent, such as a scout, a reviewer or the researcher, spawn a generic child. Its brief holds the body of that agent's `agents/<name>.md` in the mahou plugin, verbatim, followed by the task. A generic child does not load the agent file, so the brief is the only way the agent's rules reach the child.
