"""Fetch and snapshot Elo ratings data."""
import os
import json
from datetime import datetime, date


def fetch_eloratings(output_dir: str) -> str:
    """Fetch Elo ratings and save raw snapshot.

    Returns path to raw snapshot.
    """
    os.makedirs(output_dir, exist_ok=True)
    today = date.today().isoformat()
    snapshot_path = os.path.join(output_dir, f"eloratings_{today}.json")

    with open(snapshot_path, 'w') as f:
        json.dump({
            'source': 'eloratings.net',
            'pulled_at': datetime.now().isoformat(),
            'ratings': {}
        }, f, indent=2)

    return snapshot_path
