## What and why

<!-- One or two sentences. Link the issue if there is one. -->

## How it was checked

- [ ] `cd backend && ruff check app tests && pytest -q`
- [ ] `cd frontend && npm run typecheck && npm test` (if the UI changed)
- [ ] A test covers the new behaviour or the bug (new audit rule: catalogue entry, provenance set, check and test)
- [ ] Docs and `CHANGELOG.md` updated (new migration: note anything that could fail on existing data)

## Notes for the reviewer

<!-- Behaviour changes, new settings, anything that needs documenting in README, CHANGELOG or KNOWN_LIMITATIONS. -->

Numbers shown in the UI must stay honest: measured, imported, estimated or unavailable, never guessed.
