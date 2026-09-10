# Wuji Agent Integration P0

This isolated package validates one fixed `qwen-flash` model configuration. It is not connected to the production API.

The real probe is intentionally single-use against a persistent four-attempt ledger:

```sh
python -m wuji_agent_integration.probe \
  --credentials /private/path/credential.json \
  --ledger /private/path/call-ledger.json \
  --report /private/path/report.json
```

The harness process receives only the credential path. A spawned Provider process validates and reads the `0600` JSON file, creates the native protocol client, reserves each upstream attempt, and returns serialized framework messages. The CLI strips provider keys from its environment and disables external tracing before importing model or Harness code.

Run the local cancellation fixture without credentials or network access:

```sh
python -m wuji_agent_integration.probe --fixture-cancel
```
