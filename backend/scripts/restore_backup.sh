#!/usr/bin/env bash
# Restore an encrypted nightly backup (see .github/workflows/db-backup.yml).
#
#   CONFIRM_RESTORE=yes scripts/restore_backup.sh <backup.dump.age> <age-key-file> <target-database-url>
#
# Download the file first, e.g.:
#   aws s3 cp s3://<bucket>/db/<file>.dump.age . --endpoint-url https://<account>.r2.cloudflarestorage.com
#
# The target's public-schema objects are DROPPED and replaced (--clean). For the
# monthly restore drill, point it at a scratch database, never at production.
# Needs: age, pg_restore (version >= the server's major version).
set -euo pipefail

if [ $# -ne 3 ]; then
  echo "usage: CONFIRM_RESTORE=yes $0 <backup.dump.age> <age-key-file> <target-database-url>" >&2
  exit 2
fi
backup="$1"; key="$2"; target="$3"

if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
  echo "Refusing to run: this replaces data in the target database." >&2
  echo "Re-run with CONFIRM_RESTORE=yes once you are sure the target is right." >&2
  exit 1
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
age -d -i "$key" -o "$tmp" "$backup"
pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error -d "$target" "$tmp"
echo "Restored $backup into the target database."
echo "Check row counts, e.g.: psql \"<target>\" -c 'select count(*) from users;'"
