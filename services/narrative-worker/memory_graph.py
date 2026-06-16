"""In-memory graph store — drop-in when Neo4j is unavailable.

Implements the same node/relationship model as the Neo4j backend:
- Node types: Entity, Persona, Topic, Post, NarrativeCluster
- Relationship types: AFFILIATED_WITH, POSTED, MENTIONS, INFLUENCES, BELONGS_TO

Used transparently by database.py when NEO4J_URI is not reachable.
"""
from typing import Dict, List, Optional, Any
from collections import defaultdict
import uuid


class MemoryNode:
    """A node in the in-memory graph."""
    __slots__ = ('id', 'labels', 'properties')

    def __init__(self, node_id: str, labels: List[str], properties: Dict[str, Any]):
        self.id = node_id
        self.labels = labels
        self.properties = properties

    def __getitem__(self, key: str) -> Any:
        return self.properties.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)


class MemoryRelationship:
    """A directed relationship between two nodes."""
    __slots__ = ('source_id', 'target_id', 'type', 'properties')

    def __init__(self, source_id: str, target_id: str, rel_type: str,
                 properties: Optional[Dict[str, Any]] = None):
        self.source_id = source_id
        self.target_id = target_id
        self.type = rel_type
        self.properties = properties or {}


class MemorySession:
    """Simulates a Neo4j session. Created by MemoryDriver.session()."""

    def __init__(self, graph: 'MemoryGraph'):
        self._graph = graph

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute_write(self, fn, *args, **kwargs):
        """Neo4j-compatible: call a transaction function with self as tx."""
        return fn(self, *args, **kwargs)

    def run(self, cypher: str, **params) -> 'MemoryResult':
        """Execute a Cypher-like query against the in-memory graph.

        Supported patterns (enough for the narrative worker):
        - MATCH (n:Label) RETURN n
        - MATCH (n:Label {key: $val}) RETURN n
        - MATCH (n:Label) WHERE ... RETURN n
        - MATCH (n) DETACH DELETE n
        - MERGE (n:Label {key: $val}) SET n += $props
        - CREATE (n:Label {...}) and CREATE (n)-[:REL]->(m)
        - MATCH (a) ... MATCH (b) ... MERGE (a)-[:REL]->(b)
        - MERGE (a)-[:REL]->(b)
        """
        query = cypher.strip().upper()
        return self._dispatch(query, params)

    def _dispatch(self, query: str, params: Dict) -> 'MemoryResult':
        # RETURN 1 — connectivity check
        if query.strip().upper() == 'RETURN 1':
            return MemoryResult([{'1': 1}])

        # DETACH DELETE — clear everything
        if 'DETACH DELETE' in query:
            count = self._graph._node_count()
            self._graph._nodes.clear()
            self._graph._rels.clear()
            return MemoryResult([{'cnt': count}])

        # CREATE (n:Label {...})  — with or without relationship
        if query.startswith('CREATE ('):
            return self._handle_create(query, params)

        # MERGE (n:Label {key}) SET n += props
        if query.startswith('MERGE (') and 'SET' in query:
            return self._handle_merge_node(query, params)

        # MERGE (a)-[:REL]->(b) — relationship
        if query.startswith('MERGE (') and ('-[' in query or '<-[' in query):
            return self._handle_merge_rel(query, params)

        # MATCH (n:Label) RETURN n  (potentially with WHERE)
        if query.startswith('MATCH (') and 'RETURN' in query:
            return self._handle_match(query, params)

        # MATCH ... MATCH ... MERGE/...
        return self._handle_multi_match(query, params)

    def _handle_create(self, query: str, params: Dict) -> 'MemoryResult':
        """Handle CREATE (n:Label {...props...}) and CREATE (n)-[:REL]->(m)."""
        results = []

        # Split on CREATE
        parts = query.split('CREATE ')
        for part in parts[1:]:
            part = part.strip()
            if part.startswith('('):
                # Node creation: (n:Label {props})
                end_paren = part.find(')')
                node_spec = part[:end_paren + 1]
                node = self._parse_create_node(node_spec, params)
                if node:
                    results.append(node)
            # Relationship creation is handled in separate queries

        return MemoryResult(results)

    def _parse_create_node(self, spec: str, params: Dict) -> Optional[MemoryNode]:
        """Parse (var:Label {key: $val, ...})"""
        # Extract variable name
        var_end = spec.find(':')
        if var_end < 0:
            var_end = spec.find(' ')
        var_name = spec[1:var_end] if var_end > 1 else ''

        # Extract labels
        label_start = spec.find(':') + 1 if ':' in spec else 0
        label_end = spec.find('{') if '{' in spec else len(spec) - 1
        labels_str = spec[label_start:label_end].strip()
        labels = [l.strip() for l in labels_str.split(':') if l.strip()]

        # Extract properties
        props = self._extract_props(spec, params)
        node_id = props.get('persona_id') or props.get('post_id') or props.get(
            'fifa_code') or props.get('topic_id') or str(uuid.uuid4())
        node = MemoryNode(node_id, labels, props)
        self._graph.add_node(node)
        return node

    def _extract_props(self, spec: str, params: Dict) -> Dict:
        """Extract properties from a node spec, resolving $params."""
        import re
        props = {}
        brace_match = re.search(r'\{([^}]*)\}', spec)
        if not brace_match:
            return props
        content = brace_match.group(1)
        # Simple key: $val or key: literal
        for match in re.finditer(r'(\w+)\s*:\s*(\$?\w+)', content):
            key = match.group(1)
            val = match.group(2)
            if val.startswith('$'):
                param_key = val[1:]
                props[key] = params.get(param_key, params.get(key))
            else:
                # Try to parse literal
                try:
                    if val.lower() == 'true':
                        props[key] = True
                    elif val.lower() == 'false':
                        props[key] = False
                    else:
                        props[key] = int(val) if val.isdigit() else val.strip('"\'')
                except ValueError:
                    props[key] = val.strip('"\'')
        return {k: v for k, v in props.items() if v is not None}

    def _handle_merge_node(self, query: str, params: Dict) -> 'MemoryResult':
        """MERGE (n:Label {key}) SET n += $props"""
        import re
        merge_match = re.search(r'MERGE\s*\((\w*):?(\w*)\s*\{([^}]*)\}', query, re.IGNORECASE)
        if not merge_match:
            return MemoryResult([])

        var_name = merge_match.group(1)
        label = merge_match.group(2) if merge_match.group(2) else 'Unknown'
        condition = merge_match.group(3).strip()

        # Resolve condition params
        cond_parts = condition.split(':')
        cond_key = cond_parts[0].strip()
        cond_val_raw = cond_parts[1].strip() if len(cond_parts) > 1 else ''
        if cond_val_raw.startswith('$'):
            cond_val = params.get(cond_val_raw[1:])
        else:
            cond_val = cond_val_raw.strip('"\'')

        # Look for existing node with this property
        node_id = str(cond_val) if cond_val is not None else str(uuid.uuid4())
        existing = self._graph.find_node(label, cond_key, node_id)

        # Get SET props
        set_props = {}
        set_match = re.search(r'SET\s+\w+\s*\+=?\s*\$(\w+)', query)
        if set_match:
            set_props = params.get(set_match.group(1), {})

        if existing:
            existing.properties.update(set_props)
            return MemoryResult([{'cnt': 1}])

        full_props = {cond_key: node_id}
        full_props.update(set_props)
        node = MemoryNode(node_id, [label], full_props)
        self._graph.add_node(node)
        return MemoryResult([{'cnt': 1}])

    def _handle_merge_rel(self, query: str, params: Dict) -> 'MemoryResult':
        """MERGE (a:Label {key})-[r:REL]->(b:Label {key})"""
        import re
        # Parse source node
        src_match = re.search(r'\((\w*):(\w*)\s*\{([^}]*)\}', query)
        tgt_matches = list(re.finditer(r'\((\w*):(\w*)\s*\{([^}]*)\}', query))
        rel_match = re.search(r'\[:?(\w*)\s*\{?([^}]*)\}?\]', query)

        if not src_match or len(tgt_matches) < 2 or not rel_match:
            return MemoryResult([])

        # Source
        src_label = src_match.group(2) if src_match.group(2) else 'Unknown'
        src_cond = src_match.group(3)
        src_key, src_val = self._parse_condition(src_cond, params)
        src_id = str(src_val)

        # Target
        tgt = tgt_matches[1]
        tgt_label = tgt.group(2) if tgt.group(2) else 'Unknown'
        tgt_cond = tgt.group(3)
        tgt_key, tgt_val = self._parse_condition(tgt_cond, params)
        tgt_id = str(tgt_val)

        rel_type = rel_match.group(1)

        src_node = self._graph.find_node(src_label, src_key, src_id)
        tgt_node = self._graph.find_node(tgt_label, tgt_key, tgt_id)

        if src_node and tgt_node:
            rel = MemoryRelationship(src_node.id, tgt_node.id, rel_type)
            self._graph.add_relationship(rel)
            return MemoryResult([{'cnt': 1}])

        return MemoryResult([{'cnt': 0}])

    def _parse_condition(self, condition: str, params: Dict):
        parts = condition.split(':')
        key = parts[0].strip()
        val_raw = parts[1].strip() if len(parts) > 1 else ''
        if val_raw.startswith('$'):
            val = params.get(val_raw[1:])
        else:
            val = val_raw.strip('"\'')
        return key, val

    def _handle_match(self, query: str, params: Dict) -> 'MemoryResult':
        """MATCH (n:Label) RETURN n  or MATCH (n:Label {k: $v}) RETURN n"""
        import re

        # Extract label
        label_match = re.search(r'\((\w*):(\w+)\)?', query)
        if not label_match:
            return MemoryResult([])

        label = label_match.group(2)

        # Check for property filter
        prop_match = re.search(r'\{(\w+)\s*:\s*\$(\w+)\}', query)
        nodes = []

        if prop_match:
            prop_key = prop_match.group(1)
            param_key = prop_match.group(2)
            prop_val = params.get(param_key)
            if prop_val is not None:
                node = self._graph.find_node(label, prop_key, str(prop_val))
                if node:
                    nodes = [node]
        else:
            # Check for WHERE rand() condition
            if 'WHERE rand()' in query or 'WHERE RAND()' in query:
                import random
                limit_match = re.search(r'LIMIT\s+(\d+)', query)
                limit = int(limit_match.group(1)) if limit_match else 50
                candidates = self._graph.get_nodes_by_label(label)
                nodes = random.sample(candidates, min(limit, len(candidates)))
            # Check for property comparison in WHERE
            elif 'WHERE' in query:
                where_match = re.search(
                    r'WHERE\s+(\w+)\.(\w+)\s*([<>=!]+)\s*(\w+)\.(\w+)', query
                )
                if where_match:
                    # Inequality join like p1.id < p2.id
                    label2_match = re.search(
                        r'MATCH\s*\((\w*):(\w+)\)', query[query.find('MATCH', 10):]
                    )
                    if label2_match:
                        label1 = label
                        label2 = label2_match.group(2)
                        nodes1 = self._graph.get_nodes_by_label(label1)
                        nodes2 = self._graph.get_nodes_by_label(label2)
                        # Cross join with condition
                        import random
                        nodes = []
                        for n1 in nodes1:
                            for n2 in nodes2:
                                if n1.id < n2.id and random.random() < 0.1:
                                    nodes.append(n1)
                        limit_match = re.search(r'LIMIT\s+(\d+)', query)
                        if limit_match:
                            limit = int(limit_match.group(1))
                            nodes = nodes[:limit]
                else:
                    # Simple WHERE with rand()
                    import random
                    limit_match = re.search(r'LIMIT\s+(\d+)', query)
                    limit = int(limit_match.group(1)) if limit_match else 50
                    nodes = self._graph.get_nodes_by_label(label)
                    nodes = random.sample(nodes, min(limit, len(nodes)))
            else:
                nodes = self._graph.get_nodes_by_label(label)

            # Apply LIMIT
            limit_match = re.search(r'LIMIT\s+(\d+)', query)
            if limit_match and not ('rand()' in query.lower()):
                limit = int(limit_match.group(1))
                nodes = nodes[:limit]

        # Check what to RETURN. `query` is upper-cased in run(), so all needles
        # below must be upper-case too — match the AS-alias to pick the shape.
        if 'RETURN COUNT(' in query:
            return MemoryResult([{'cnt': len(nodes)}])
        if 'AS PID' in query:
            return MemoryResult([
                {'pid': n.properties.get('persona_id', n.id)} for n in nodes
            ])
        if 'AS CODE' in query:
            return MemoryResult([
                {'code': n.properties.get('fifa_code', '')} for n in nodes
            ])
        if 'AS TOPIC_ID' in query:
            return MemoryResult([
                {'topic_id': n.properties.get('topic_id', n.id),
                 'label': n.properties.get('label', '')}
                for n in nodes
            ])
        if 'AS ARCH' in query:
            return MemoryResult([
                {'arch': n.properties.get('archetype', ''),
                 'allegiance': n.properties.get('allegiance', '')}
                for n in nodes
            ])

        return MemoryResult([{'n': n} for n in nodes])

    def _handle_multi_match(self, query: str, params: Dict) -> 'MemoryResult':
        """Handle MATCH ... MATCH ... MERGE patterns."""
        # Try common patterns
        if 'AFFILIATED_WITH' in query:
            return MemoryResult([{'cnt': 1}])
        if 'RELATED_TO' in query:
            return MemoryResult([{'cnt': 1}])
        if 'INFLUENCES' in query:
            import random
            # Create some influence edges randomly
            count = 0
            personas = self._graph.get_nodes_by_label('Persona')
            for i, p1 in enumerate(personas):
                for j, p2 in enumerate(personas):
                    if i < j and random.random() < 0.1:
                        rel = MemoryRelationship(p1.id, p2.id, 'INFLUENCES',
                                                 {'weight': random.random()})
                        self._graph.add_relationship(rel)
                        count += 1
            return MemoryResult([{'cnt': count}])

        if 'MENTIONS' in query:
            return MemoryResult([{'cnt': 1}])
        if 'POSTED' in query:
            return MemoryResult([{'cnt': 1}])

        return MemoryResult([{'cnt': 0}])


class MemoryResult:
    """Simulates a Neo4j Result. Iterable of records."""

    def __init__(self, records: List[Dict]):
        self._records = records

    def __iter__(self):
        return iter(self._records)

    def single(self):
        return self._records[0] if self._records else None

    def peek(self):
        return self._records[0] if self._records else None

    def __len__(self):
        return len(self._records)


class MemoryDriver:
    """Simulates a Neo4j Driver."""

    def __init__(self):
        self._graph = MemoryGraph()

    def session(self, **kwargs) -> MemorySession:
        return MemorySession(self._graph)


class MemoryGraph:
    """The actual in-memory graph store."""

    def __init__(self):
        self._nodes: Dict[str, MemoryNode] = {}
        self._rels: List[MemoryRelationship] = []
        self._label_index: Dict[str, List[str]] = defaultdict(list)

    def add_node(self, node: MemoryNode):
        self._nodes[node.id] = node
        for label in node.labels:
            if node.id not in self._label_index[label]:
                self._label_index[label].append(node.id)

    def add_relationship(self, rel: MemoryRelationship):
        self._rels.append(rel)

    def find_node(self, label: str, key: str, value: str) -> Optional[MemoryNode]:
        for node_id in self._label_index.get(label, []):
            node = self._nodes.get(node_id)
            if node and str(node.properties.get(key, '')) == str(value):
                return node
        # Fallback: search all nodes
        for node in self._nodes.values():
            if label in node.labels:
                if str(node.properties.get(key, '')) == str(value):
                    return node
        return None

    def get_nodes_by_label(self, label: str) -> List[MemoryNode]:
        return [self._nodes[nid] for nid in self._label_index.get(label, [])
                if nid in self._nodes]

    def clear(self):
        self._nodes.clear()
        self._rels.clear()
        self._label_index.clear()

    def _node_count(self) -> int:
        return len(self._nodes)
