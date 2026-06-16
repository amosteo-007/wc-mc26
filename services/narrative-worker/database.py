"""Neo4j + Redis operations for narrative worker.

When Neo4j is unreachable, falls back to an in-memory graph so the
narrative pipeline still runs end-to-end for development and testing.
"""
import os
import logging
from typing import Optional, Union
import redis

from memory_graph import MemoryDriver

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'wc2026_dev')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

_driver: Optional[Union['neo4j.Driver', MemoryDriver]] = None
_driver_type: str = ''  # 'neo4j' | 'memory'
_redis = None


def _try_neo4j():
    """Attempt to connect to Neo4j. Returns a Driver or raises."""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # Verify connectivity with a simple query
    with driver.session() as session:
        session.run("RETURN 1")
    return driver


def get_driver():
    """Return a graph driver (Neo4j or in-memory).

    Tries Neo4j first; falls back to an in-memory store if Neo4j
    isn't reachable so the service stays usable in dev / CI.
    """
    global _driver, _driver_type
    if _driver is not None:
        return _driver

    # Try real Neo4j
    try:
        _driver = _try_neo4j()
        _driver_type = 'neo4j'
        logger.info("Connected to Neo4j at %s", NEO4J_URI)
        return _driver
    except Exception:
        logger.warning(
            "Neo4j unavailable at %s — using in-memory graph. "
            "Narrative output is valid but graph stats will be approximate.",
            NEO4J_URI
        )

    # Fallback to memory graph
    _driver = MemoryDriver()
    _driver_type = 'memory'
    return _driver


def is_memory_backend() -> bool:
    """Return True if the in-memory graph is active."""
    get_driver()  # ensure initialized
    return _driver_type == 'memory'


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def clear_graph():
    """Remove all nodes and relations for a fresh run."""
    driver = get_driver()
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def get_node_count() -> int:
    driver = get_driver()
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS cnt")
        record = result.single()
        return record['cnt'] if record else 0


def get_relation_count() -> int:
    driver = get_driver()
    with driver.session() as session:
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
        record = result.single()
        return record['cnt'] if record else 0


# ---------------------------------------------------------------------------
# Transaction helpers — the graph_builder / persona modules call these via
# session.execute_write(fn, ...) with Neo4j, or they can call session.run()
# directly through the memory session.
# ---------------------------------------------------------------------------

def create_entity(
    tx, entity_type: str, fifa_code: str, name: str, properties: dict = None
):
    """Create an Entity node."""
    props = {'fifa_code': fifa_code, 'name': name, 'type': entity_type}
    if properties:
        props.update(properties)
    tx.run("""
        MERGE (e:Entity {fifa_code: $fifa_code})
        SET e += $props
    """, fifa_code=fifa_code, props=props)


def create_persona(
    tx, persona_id: str, archetype: str, allegiance: str,
    influence: float, properties: dict = None
):
    """Create a Persona node."""
    props = {
        'persona_id': persona_id,
        'archetype': archetype,
        'allegiance': allegiance,
        'influence': influence,
        'memory_budget': 2000,
        'network_position': 'periphery'
    }
    if properties:
        props.update(properties)
    tx.run("""
        CREATE (p:Persona)
        SET p += $props
    """, props=props)


def connect_persona_to_entity(tx, persona_id: str, fifa_code: str):
    """Create AFFILIATED_WITH relationship."""
    tx.run("""
        MATCH (p:Persona {persona_id: $persona_id})
        MATCH (e:Entity {fifa_code: $fifa_code})
        MERGE (p)-[:AFFILIATED_WITH]->(e)
    """, persona_id=persona_id, fifa_code=fifa_code)


def session_execute_write(fn, *args, **kwargs):
    """Call a transaction function against the current driver.

    Works with both Neo4j (real transactions) and the memory backend
    (where the session itself acts as the tx).
    """
    driver = get_driver()
    if is_memory_backend():
        # MemorySession acts as its own transaction
        with driver.session() as session:
            return fn(session, *args, **kwargs)
    else:
        with driver.session() as session:
            return session.execute_write(fn, *args, **kwargs)
