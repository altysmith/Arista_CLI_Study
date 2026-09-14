# Private Raspberry Pi deployment

This app is a lightweight Python simulation, not vEOS or a hypervisor.

## Layout

- Host: existing Altylab Raspberry Pi, user `ealtenho`.
- App root: `/home/ealtenho/arista-study`.
- Source: versioned folders in `releases/`; `current` points to the active release.
- Data: `user_data/progress.sqlite3`, outside releases. Never replace it on deployment.
- Service: `arista-study.service`, bound only to `127.0.0.1:8772`.
- Public address: `https://arista.altylab.com`, protected by its own Cloudflare Access application and the existing owner-only policy.
- Existing locally managed Cloudflare Tunnel. Do not create or migrate a tunnel.
- Tunnel ingress must validate the new application's exact audience with `originRequest.access.required: true`.

The application assumes a single authorized owner. Saved exercises are shared across that owner's devices. It is not a multi-user service. Never broaden Access policies without implementing user isolation first. No shell commands or real network operations are executed by the simulated terminal.

## Release checks

1. Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` and `node --check src/arista_sim/web_assets/app.js` locally.
2. Package source, tests, and deploy files only. Exclude user data, caches, credentials, and Git metadata.
3. Extract into a new release directory on the Pi; run the Python suite there.
4. Back up existing data with `deploy/backup.py` before switching releases.
5. Update `current`, then restart only `arista-study.service`.
6. Check `/api/labs`, exercise grading, snapshot recovery, and service status. Use an isolated temporary database for test traffic.
7. Verify anonymous requests to `/` and API paths receive Cloudflare Access redirects rather than app content. The owner must verify sign-in from their browser.

Back up tunnel configuration before adding this one ingress rule, validate with `cloudflared tunnel ingress validate`, then restart the existing tunnel service. Check all existing app routes afterwards. Install the included backup service and timer; backups use SQLite's online backup API, run integrity checks, and keep the latest 14 copies.

## Recovery

For code rollback, point `current` at the preceding release and restart `arista-study.service`. Keep the live database intact. If restoring data is explicitly required, stop this service, copy the current database to a safety backup, restore a verified backup to `user_data/progress.sqlite3`, preserve owner and mode 0600, then restart. Code rollback does not automatically downgrade future database formats.

## Capacity

At initial inspection the Pi reported roughly 13 GiB available RAM, 103 GB free disk, and a 0.16 one-minute load average. This is a point-in-time reading, not a peak-load assessment. This service has a 256 MB memory limit; up to 64 sessions are cached, with durable snapshots stored in SQLite. Keep the configuration simulator here; assess separate hardware if moving to multiple real EOS VMs.
