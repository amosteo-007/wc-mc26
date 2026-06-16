"""Daily scheduler loop for the live WC2026 results fetcher.

Runs ``pipeline.ingest.wc_results.refresh()`` immediately on start, then once
every ``WC_REFRESH_INTERVAL`` seconds (default 24h). Intended to run as a
long-lived compose service so the wizard's tournament tables track real scores
without any host-side cron. A failed fetch is logged and retried on the next
tick rather than killing the loop.
"""
import os
import sys
import time
from datetime import datetime, timezone

from pipeline.ingest.wc_results import refresh

INTERVAL = int(os.getenv('WC_REFRESH_INTERVAL', str(24 * 60 * 60)))


def _log(msg: str) -> None:
    print(f'[scheduler {datetime.now(timezone.utc).isoformat()}] {msg}', flush=True)


def run() -> None:
    _log(f'starting; refreshing every {INTERVAL}s')
    while True:
        try:
            n = refresh()
            _log(f'refresh ok — upserted {n} played match(es)')
        except Exception as exc:  # noqa: BLE001 — keep the loop alive on failure
            _log(f'refresh failed: {exc}')
        time.sleep(INTERVAL)


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)
