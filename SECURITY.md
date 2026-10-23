# Security

Do not submit credentials or private traces in public issues. Report a vulnerability privately through GitHub private vulnerability reporting if enabled; otherwise contact the maintainer via the profile contact method before sharing exploit details.

The expression interpreter is a bounded execution surface, not a sandbox for arbitrary Python. The fixed host owns permissions, tenant isolation, scoring and approval. Generated candidates cannot change those boundaries. Source text, papers, old prompts and tool results remain untrusted evidence. Filtering is not a guarantee against poisoning.

The community server is intended for local/self-hosted testing. Production operation additionally requires TLS termination, authenticated owner control-plane access, abuse/rate limits, backups, retention operations and deployment review. Full traces may contain personal information even after masking. Participation is optional and requires explicit scoped consent.

Use only public or authorized synthetic data in public experiment exports. Never publish `.env`, keys, user uploads, approval signing material or private workspaces.

Historical `frozen-source/` copies retain the exact pre-release experiment clients, including transport behavior later hardened. They are audit evidence and are not the maintained package. The historical reproduction wrapper explicitly enforces HTTPS, denies redirects and disables environment proxies, and records that transport safety overlay as a new reproduction contract. Use the current client for new work.
