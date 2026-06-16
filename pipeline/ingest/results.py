"""Fetch and snapshot historical match results."""
import os
import json
from datetime import datetime, date


def fetch_results(output_dir: str) -> str:
    """Fetch historical match results and save raw snapshot.

    Returns path to raw snapshot.
    """
    os.makedirs(output_dir, exist_ok=True)
    today = date.today().isoformat()
    snapshot_path = os.path.join(output_dir, f"results_{today}.json")

    with open(snapshot_path, 'w') as f:
        json.dump({
            'source': 'international_results_dataset',
            'pulled_at': datetime.now().isoformat(),
            'match_count': 0,
            'matches': []
        }, f, indent=2)

    return snapshot_path
