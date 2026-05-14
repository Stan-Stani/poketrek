# moneo-sense-sweep audit run

- shards/  — one JSON manifest per auditor task (3 total)
- prompts/ — rendered audit prompt to feed each LLM auditor
- flags/   — drop the auditors' flag-*.json outputs here
- after auditors finish, run validate → aggregate → reviewer UI → apply
