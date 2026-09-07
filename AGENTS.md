# Codex Search Plugin - Contributor Gates

## Scope

This standalone backend registers `codex` for native Hermes `web_search`.
Do not modify Hermes core or production gateways as part of plugin work.
Keep credentials, private endpoints, customer data, and machine-specific configuration out of this repository and command output.

## Change and release gates

- Add a behavioral regression test for a bug fix. For HTTP identity changes, assert the outgoing request carries an explicit plugin User-Agent rather than relying on Python's default identity.
- Bump `plugin.yaml` with a patch version for a released bug fix. Keep the User-Agent version consistent with the manifest.
- Preserve concurrent remote changes: fetch and inspect divergence before integrating. Never force-push shared history.
- Run `python -m unittest discover -s tests -v`, `hermes plugins doctor . --ci`, and `git diff --check` before publishing.
- Review the intended diff for secrets and unrelated changes, then commit and push. Read back the remote branch SHA before claiming publication succeeded.
- If GitHub Actions workflows are present, verify the target commit's CI succeeds. If none exist, report that rather than claiming CI passed.

## Native installation verification

- Use `hermes plugins install <repository-url> --ref <full-40-character-commit-sha> --enable` in disposable `HOME` and `HERMES_HOME` directories under `/tmp`, with a minimal credential-free child environment and default security scanning enabled.
- Read back the installed Git HEAD, manifest version, and enabled state. Run Plugin Doctor against that installed checkout. Local unit tests and Doctor alone do not verify the customer installation path.
- Clean up disposable verification directories. Do not modify other existing Hermes profiles.
- When updating the user's installation is authorized, use the native installer with `--force --ref <sha> --enable`; do not manually patch installed files. Inspect existing installation state first and preserve any unexplained local changes.
- Read back the exact installed HEAD and enabled state and run `hermes plugins doctor web-codex --ci`.

## Live behavior verification

- Exercise the installed provider in a fresh process with the configured endpoint and authorized credentials. Never print credential values or raw private response bodies.
- Report success, error category/status, result count, and whether output exists. A successful result from another backend is not a Codex verification.
- Distinguish a direct installed-provider probe from native wrapper dispatch and Telegram gateway verification. Report which paths were actually exercised.
- For isolated native `web_search` wrapper tests, disable `web.keyless_rescue` only in the disposable profile so fallback cannot mask failure. Never change live routing merely to run a test.
- HTTP 403, HTTP 503, or another upstream failure is not an end-to-end pass. Report the blocker without guessing its cause; unit/install success and live backend success are separate gates.

## Gateway boundary and completion report

Native installation does not reload modules in an already-running gateway. Gateway restarts are the user's operation: provide `hermes gateway restart` and wait for confirmation before verifying Telegram's updated `web_search` path. Never restart or schedule a restart yourself.

Report version, commit, remote publication state, tests, clean-install result, installed SHA, live result, working-tree state, and any pending gateway verification. Do not say "only restart remains" until publication and the intended installation have both been verified.
