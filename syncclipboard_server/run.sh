#!/bin/sh
set -eu
umask 077
# Validate before extracting. Reject newlines so command substitution cannot
# silently trim a password; quotes and backslashes are handled by jq.
if ! jq -e '
  (.username | type == "string" and test("^[A-Za-z0-9_-]{1,64}$")) and
  (.password | type == "string" and length >= 16 and
    (contains("\n") | not) and (contains("\r") | not) and (contains("\u0000") | not))
' /data/options.json >/dev/null 2>&1; then
    echo 'Invalid options: username must use letters, digits, _ or -; password needs 16+ characters without line breaks.' >&2
    exit 1
fi
SYNCCLIPBOARD_USERNAME=$(jq -r '.username' /data/options.json)
SYNCCLIPBOARD_PASSWORD=$(jq -r '.password' /data/options.json)
export SYNCCLIPBOARD_USERNAME SYNCCLIPBOARD_PASSWORD
cd /app
exec dotnet SyncClipboard.Server.dll --contentRoot /data
