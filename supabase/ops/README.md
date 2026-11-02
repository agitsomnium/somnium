# Classroom backup operations

`backup_classroom.py /absolute/private/new-output-folder` reads the explicitly named Somnium test project through the existing authenticated Supabase CLI. It does not depend on a copied `w/` linked-project directory. Its output is plaintext personal data: the output directory is0700, then the authorized operator must encrypt it and remove the generated plaintext after verification. Never upload plaintext or credentials. The code does not print keys or row values.

The 2026-11-02 Codex completion run queried16 tables/258 rows and fetched11 Storage objects(7,367,016bytes). The encrypted result was decrypted into a temporary directory, restored to isolated PostgreSQL and checked against row counts, object hashes and role tests. This verifies logical DB/data restoration, not an independent running GoTrue authentication service. Auth sessions/passwords/SMTP secrets are excluded and must be provisioned separately.

Institution copy: Google Drive folder `강의실_백업`, owner agit.somnium@gmail.com, restricted to that account; upload was downloaded again and SHA256 matched. Latest file:
https://drive.google.com/file/d/1p33N1QQ_BPW-NiH5Cwm0EZ-CeQ9czx24/view
SHA256 `788d674c838c3406b1ac5af569938fdec81024fb70dab065da8880fbac0fc0c9`.

Encryption passphrase remains only in macOS Keychain service `somnium-classroom-backup-20261102`; never include its value in documents, terminal output or model inputs. A second authorized custodian and institution-owned secret vault have not been designated. A future operator must arrange that handoff securely before relying on recovery without this Mac. No recurring backup scheduler was added or claimed.

## Backup decryption + integrity check (not a restore test)
`decrypt_integrity_check.py ENCRYPTED_FILE` decrypts with a hidden passphrase prompt and verifies the manifest row counts and file hashes. It restores nothing.

## Erasure ledger (member deletion)
After the erasure draft is applied, run `erasure_ledger.py --ref <project> export --out-dir <private dir> --store-dir <institution folder>` after every deletion; only an `OK export` line counts. After restoring any backup, run `erasure_ledger.py --ref <project> apply --file <stored ledger>`; only an `OK apply` line counts. `verify` checks a stored file against the live database. Any `FAILED` line means not done. The ledger holds one-way hashes only.
