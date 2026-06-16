"""Instantiate crowd from archetypes. Never clone identical agents."""
import uuid
import numpy as np
from typing import Dict, List
from database import get_driver


def generate_personas(
    driver,
    audience_scope: List[str],
    tier: str,
    world_spec: Dict,
    model_client=None
) -> List[str]:
    """Generate differentiated persona instances.

    Creates crowd variants from archetypes. Each persona gets randomized
    variation in influence, stance_priors, and network position.
    """
    tier_config = {
        'quick': {'multiplier': 10},
        'analyst': {'multiplier': 40},
        'executive': {'multiplier': 100}
    }
    config = tier_config.get(tier, tier_config['quick'])

    archetypes = [
        {'id': 'transfer_insider', 'base_influence': 0.7, 'network': 'core'},
        {'id': 'club_scout', 'base_influence': 0.5, 'network': 'core'},
        {'id': 'selling_club_fan', 'base_influence': 0.2, 'network': 'bridge'},
        {'id': 'buying_club_fan', 'base_influence': 0.25, 'network': 'bridge'},
        {'id': 'agent_source', 'base_influence': 0.6, 'network': 'core'},
        {'id': 'beat_reporter', 'base_influence': 0.45, 'network': 'core'},
        {'id': 'market_analyst', 'base_influence': 0.4, 'network': 'core'},
        {'id': 'rumor_aggregator', 'base_influence': 0.3, 'network': 'periphery'},
        {'id': 'casual_follower', 'base_influence': 0.05, 'network': 'periphery'},
    ]

    with driver.session() as session:
        result = session.run(
            "MATCH (e:Entity {type: 'team'}) RETURN e.fifa_code AS code"
        )
        team_codes = [r['code'] for r in result]

    if not team_codes:
        team_codes = ['neutral']

    rng = np.random.default_rng()
    persona_ids = []

    with driver.session() as session:
        for arch in archetypes:
            n_instances = max(1, int(arch['base_influence'] * config['multiplier']))

            for i in range(n_instances):
                pid = f"persona_{arch['id']}_{i}_{uuid.uuid4().hex[:6]}"

                influence = arch['base_influence'] * rng.uniform(0.8, 1.2)
                influence = min(influence, 1.0)

                allegiance = 'neutral'
                if arch['id'] in ('transfer_insider', 'selling_club_fan', 'buying_club_fan',
                                   'club_scout', 'beat_reporter'):
                    allegiance = team_codes[rng.integers(0, len(team_codes))]

                stance_priors = {
                    'optimism': rng.uniform(0.3, 0.9),
                    'criticism': rng.uniform(0.1, 0.7),
                    'engagement': rng.uniform(0.3, 1.0),
                    'polarization': rng.uniform(0.1, 0.6)
                }

                props = {
                    'persona_id': pid,
                    'archetype': arch['id'],
                    'allegiance': allegiance,
                    'influence': influence,
                    'memory_budget': 2000,
                    'network_position': arch['network'],
                    'response_speed': rng.uniform(0.0, 1.0),
                    'stance_priors': str(stance_priors)
                }

                session.run("""
                    CREATE (p:Persona)
                    SET p += $props
                """, props=props)

                if allegiance != 'neutral':
                    session.run("""
                        MATCH (p:Persona {persona_id: $pid})
                        MATCH (e:Entity {fifa_code: $allegiance})
                        MERGE (p)-[:AFFILIATED_WITH]->(e)
                    """, pid=pid, allegiance=allegiance)

                persona_ids.append(pid)

    return persona_ids


def assign_network_positions(personas: List[str]) -> Dict:
    """Assign network positions and create influence edges."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (p1:Persona), (p2:Persona)
            WHERE p1.persona_id < p2.persona_id AND rand() < 0.1
            MERGE (p1)-[:INFLUENCES {weight: rand()}]->(p2)
            RETURN count(*) AS cnt
        """)
        record = result.single()
        return {'edges_created': record['cnt'] if record else 0}
