"""Interview questions. One package per question; each owns its data, packet and answer keys.

A question directory holds the language-neutral material — `datasets.json`, `packet.md`,
`INSTRUCTIONS.md` — plus one subdirectory per language implementing it. The only required
file is `sync.py`: `mise run sync <name>` runs it, `mise run sync` runs every one. That is
the whole contract, so adding a question is adding a directory.
"""
