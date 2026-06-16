"""Build Neo4j knowledge graph from world spec + context packs."""
from typing import Dict, List
from database import (
    get_driver, clear_graph, get_node_count,
    create_entity, create_persona
)


def build_entity_graph(driver, world_spec: Dict) -> int:
    """Create Entity nodes from world spec outcome data."""
    with driver.session() as session:
        outcome = world_spec.get('outcome_summary', {})
        top_champions = outcome.get('top_champions', [])

        for entry in top_champions:
            team = entry.get('team', '')
            session.execute_write(
                create_entity, 'team', team, team,
                {'champion_probability': entry.get('probability', 0)}
            )

        for host in ['USA', 'MEX', 'CAN']:
            session.execute_write(create_entity, 'host', host, host)

        session.execute_write(
            create_entity, 'tournament', 'WC2026', '2026 World Cup',
            {'total_matches': 104, 'num_teams': 48}
        )

    return get_node_count()


def load_persona_archetypes(driver, packs: List[str]) -> int:
    """Load persona archetype templates from packs config."""
    archetypes = {
        'fan': [
            {'id': 'domestic_ultra', 'influence': 0.3, 'network': 'core'},
            {'id': 'domestic_casual', 'influence': 0.15, 'network': 'periphery'},
            {'id': 'rival_fan', 'influence': 0.2, 'network': 'bridge'},
            {'id': 'neutral_observer', 'influence': 0.05, 'network': 'periphery'},
        ],
        'sponsor': [
            {'id': 'brand_manager', 'influence': 0.5, 'network': 'core'},
            {'id': 'sponsor_analyst', 'influence': 0.3, 'network': 'bridge'},
        ],
        'media': [
            {'id': 'host_broadcaster', 'influence': 0.6, 'network': 'core'},
            {'id': 'regional_journalist', 'influence': 0.3, 'network': 'bridge'},
            {'id': 'digital_influencer', 'influence': 0.4, 'network': 'core'},
        ],
        'political': [
            {'id': 'government_actor', 'influence': 0.5, 'network': 'core'},
        ],
        'online': [
            {'id': 'platform_user', 'influence': 0.1, 'network': 'periphery'},
        ]
    }

    count = 0
    for pack in packs:
        if pack in archetypes:
            for arch in archetypes[pack]:
                persona_id = f"archetype_{arch['id']}"
                with driver.session() as session:
                    session.execute_write(
                        create_persona, persona_id, arch['id'],
                        'neutral', arch['influence'],
                        {'network_position': arch['network']}
                    )
                count += 1

    return count


def build_topic_graph(driver, world_spec: Dict) -> int:
    """Create Topic nodes from world spec themes."""
    topics = [
        {'id': 'transfer_rumor', 'label': 'Transfer Rumor',
         'salience': 0.9, 'sentiment': 0.0},
        {'id': 'market_value_shift', 'label': 'Market Value Shift',
         'salience': 0.8, 'sentiment': 0.1},
        {'id': 'release_clause', 'label': 'Release Clause Activity',
         'salience': 0.7, 'sentiment': 0.0},
        {'id': 'bidding_war', 'label': 'Bidding War',
         'salience': 0.75, 'sentiment': 0.2},
        {'id': 'contract_renewal', 'label': 'Contract Renewal',
         'salience': 0.65, 'sentiment': 0.1},
        {'id': 'breakout_player', 'label': 'Breakout Player',
         'salience': 0.85, 'sentiment': 0.3},
        {'id': 'agent_movement', 'label': 'Agent Movement',
         'salience': 0.6, 'sentiment': 0.0},
        {'id': 'news_break', 'label': 'Breaking News',
         'salience': 0.9, 'sentiment': 0.0},
    ]

    with driver.session() as session:
        for topic in topics:
            session.run("""
                MERGE (t:Topic {topic_id: $topic_id})
                SET t += $props
            """, topic_id=topic['id'], props={
                'label': topic['label'],
                'salience': topic['salience'],
                'sentiment': topic['sentiment']
            })

    return len(topics)


def expand_relations(driver, model_client=None) -> int:
    """GraphRAG-style expansion: discover relations between entities."""
    relations_added = 0
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Persona), (e:Entity)
            WHERE p.allegiance = e.fifa_code OR p.allegiance = 'neutral'
            MERGE (p)-[:AFFILIATED_WITH]->(e)
            RETURN count(*) AS cnt
        """)
        record = result.single()
        if record:
            relations_added += record['cnt']

        session.run("""
            MATCH (t1:Topic), (t2:Topic)
            WHERE t1.topic_id < t2.topic_id
            MERGE (t1)-[:RELATED_TO]->(t2)
        """)

    return relations_added


def build_full_graph(
    driver, world_spec: Dict, packs: List[str], model_client=None
) -> Dict:
    """Full graph construction pipeline. Returns graph statistics."""
    clear_graph()

    entities = build_entity_graph(driver, world_spec)
    personas = load_persona_archetypes(driver, packs)
    topics = build_topic_graph(driver, world_spec)
    relations = expand_relations(driver, model_client)

    return {
        'entity_count': entities,
        'persona_count': personas,
        'topic_count': topics,
        'relation_count': relations,
        'total_nodes': entities + personas + topics
    }
