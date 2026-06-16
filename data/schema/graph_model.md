# Neo4j Graph Model — Narrative Simulation

## Node types

### Entity
- `fifa_code`: string (e.g. 'BRA')
- `name`: string
- `type`: enum [team, player, sponsor, venue, media_outlet, political_body, fan_base]
- `properties`: JSON

### Persona (instantiated from archetypes in packs)
- `persona_id`: string
- `archetype`: string (e.g. 'brazilian_ultra', 'neutral_casual', 'sponsor_brand_manager')
- `influence`: float 0..1
- `memory_budget`: int (tokens)
- `network_position`: enum [core, bridge, periphery]
- `stance_priors`: JSON
- `allegiance`: string (fifa_code or 'neutral')

### Topic
- `topic_id`: string
- `label`: string
- `salience`: float 0..1
- `sentiment`: float -1..1

### NarrativeCluster
- `cluster_id`: string
- `label`: string (e.g. "sponsor backlash", "national pride surge")
- `dominance`: float 0..1
- `agent_count`: int
- `key_terms`: [string]

## Relation types

- `(Persona)-[:AFFILIATED_WITH]->(Entity)` — allegiance/employment
- `(Persona)-[:POSTED]->(Post)` — authored content
- `(Post)-[:MENTIONS]->(Topic)` — what the post is about
- `(Post)-[:REPLIES_TO]->(Post)` — reply chain
- `(Post)-[:AMPLIFIES]->(Post)` — share/retweet
- `(Persona)-[:INFLUENCES]->(Persona)` — weighted influence edge
- `(Topic)-[:RELATED_TO]->(Topic)` — topic co-occurrence
- `(Persona)-[:BELONGS_TO]->(NarrativeCluster)` — cluster membership
- `(NarrativeCluster)-[:EVOLVES_INTO]->(NarrativeCluster)` — temporal evolution

## Graph construction pipeline (MiroFish stage 4)
1. **Seed extraction** — world spec + context packs → initial entities and topics
2. **GraphRAG expansion** — query cheap model to expand relations between existing nodes
3. **Persona instantiation** — archetypes × audience scope → Persona nodes with differentiated properties
4. **Round updates** — each simulation round adds Posts and updates Topic salience/sentiment
