# AgentSINC workspace inspection security

## Purpose

Local agents need real project context to answer architecture and codebase questions accurately. This feature provides bounded, read-only access to text files under one configured workspace directory. It does not give Ollama an unrestricted filesystem, shell or external tool.

## Workspace root

By default, the root is the AgentSINC repository directory (the parent of `backend/` and `frontend/`). It can be explicitly set by the local operator:

    $env:AGENTSINC_WORKSPACE_ROOT = "E:\\AgentSINC"

The API listens on `127.0.0.1` and CORS is limited to the local AgentSINC frontend origins.

## Allowed files and limits

- Text/source extensions only: Python, TypeScript/JavaScript, JSON, Markdown, YAML, TOML, CSS, SQL, shell/PowerShell and selected compiled-language source.
- Individual file maximum: 128 KB.
- Workspace inventory maximum: 1,600 files and 24 MB of scanned source.
- Search reads a maximum of 16 KB from each candidate file.
- A mission receives no more than 22,000 characters of assembled project context.
- File-read endpoint truncates output to a bounded character limit.
- These bounds are intended to keep local retrieval responsive and model context controlled.

## Exclusions

- Git metadata, dependency folders, virtual environments, caches, build output, coverage and test output.
- Hidden directories other than the explicitly allowed GitHub metadata path in the path policy.
- `.env` files, common credential files, private-key files, databases and secret/private/credentials directories.
- Symbolic links, absolute paths, Windows drive paths and parent-directory traversal.

## Redaction

Before search snippets, file-read output or mission context is returned, common API-key, token, password, authorization, bearer-token, provider-token, AWS-key and PEM private-key patterns are replaced with redaction markers.

Redaction is defense in depth, not a guarantee that every custom or encoded secret can be recognized. Do not store secrets in source files. Keep local environment files and credentials outside the inspected source set.

## Untrusted repository content

Files are treated as untrusted data. Instructions inside source comments, Markdown, test fixtures or data files must never override the agent's system policy. The model is instructed to cite relative file paths and distinguish observed facts from assumptions.

## What this does not permit

- No file writes or deletes.
- No shell or arbitrary command execution.
- No internet browsing or external network search.
- No Git commits, pull requests, deployments, email or payments.
- No agent self-approval.

A later write/execute phase must use patch proposals, explicit human approval, isolated execution, allowlisted paths/commands, resource controls and an audit trail.

## Known limits

Retrieval uses bounded lexical matching and preferred project documents, not a semantic vector index. It can miss relevant files when terminology differs or when a project is larger than the configured scan limits. The worker reports the files actually attached to each mission so users can verify what evidence the model received.
