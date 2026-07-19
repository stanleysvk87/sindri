# import-sources

Bind-mount whatever script directories you want to scan/import from the
app's "Prehľadať priečinok" (scan folder) tab into this directory, or
add extra volume lines in `docker-compose.yml` pointing anywhere else on
the host. Read-only by default — the app never writes back to these
paths, it only reads and copies content into its own database.

Example (in `docker-compose.yml`, under `backend.volumes`):

```yaml
- /home/youruser/scripts:/import-sources/my-scripts:ro
```

Then in the app, scan `/import-sources/my-scripts`.
