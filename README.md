# agent-kit

Project tooling shared by coding agents (Claude Code, Codex, …). Everything it
produces is plain files in the project, so every agent reads the same material.

- **guides** — vendors engineering guides (Bulletproof React, TanStack Query and
  Router, NestJS, Vercel React and composition rules, the Web Interface
  Guidelines checklist, shadcn rules) from their official repositories, pinned
  to a commit or to the release tag that matches the project's lockfile.
- **mockups** — Excalidraw wireframe boards generated from code: one layout,
  frame codes derived from position, PNG export, a browsable `index.html` and a
  validator. Installs a `mockups` skill with the conventions.

## Requirements

- Python 3.11+ and git
- mockups PNG export: Node and Playwright in the project

## Run

```
uvx --from git+https://github.com/arterehin/agent-kit@v0.1.0 agent-kit <command>
```

Pin the tag in the project, for example as `package.json` scripts, so every
agent and developer runs the same version.

## Guides

```
agent-kit guides init     # guides.json with every known guide; trim it to what the project uses
agent-kit guides sync     # copy guides into .agents/vendor/<guide>/ with SOURCE.md
agent-kit guides check    # fail when a copy is missing or no longer matches the lockfile
agent-kit guides list
```

Copies are unchanged upstream files with their license and a `SOURCE.md`
(repository, ref, commit, version, license, copied files). Downloads are sparse
git fetches; nothing downloaded is executed. Sources are listed in
`agent_kit/guides/sources.json`.

## Mockups

```
agent-kit mockups init       # design/boards.json, folders and the mockups skill
agent-kit mockups build      # regenerate boards, render PNGs, write index.html, validate
agent-kit mockups check      # same, and fail if boards were out of date
agent-kit mockups validate
```

The conventions and the generator API are in `agent_kit/skills/mockups/SKILL.md`.

## Skills

`init` commands install skills into `.agents/skills/<name>/` and link them from
`.claude/skills/<name>`. `agent-kit skills sync` refreshes installed skills after
an agent-kit update.

## License

MIT
