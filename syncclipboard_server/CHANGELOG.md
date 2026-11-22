# Changelog

## 0.1.3

- Update upstream to 3.3.4 (sha256:07af92ba923196c98a237697032d4f330e44155a87d8f4791c225e9fa5a411a3).
- Passed startup, authentication, text round-trip and container-replacement persistence checks.

## 0.1.2

- Accept independent passwords of at least 16 characters.
- Verify authentication and data persistence using a generated 16-character password containing JSON escape characters.

## 0.1.1

- Package SyncClipboard Server 3.3.3 for Home Assistant OS on amd64.
- Read credentials with a JSON parser; require an independent password of at least 20 characters.
- Persist clipboard contents and history in the application's private data volume.
- Include the official icon and automated candidate-image verification.
