"""Multi-round social simulation loop. CHEAP MODEL ONLY."""
import os
import uuid
import logging
import numpy as np
from typing import Dict, List, Optional

from llm import chat as llm_chat

_log = logging.getLogger("narrative.simulation")


POST_TEMPLATES = {
    'transfer_insider': [
        "[SYNTHETIC] Hearing {player} could be on the move after that World Cup showing. Several clubs circling. Value has doubled in 3 weeks.",
        "[SYNTHETIC] Source close to {team} camp: release clause looking very achievable now. {player} representatives meeting this week.",
        "[SYNTHETIC] European clubs already making calls about {player}. {team} won't sell cheap — expect a bidding war.",
        "[SYNTHETIC] Exclusive: {player} release clause at €{value}M. After this tournament, that's looking like a bargain.",
    ],
    'club_scout': [
        "[SYNTHETIC] Scouting report: {player} stock rising fast. Physical profile + tournament experience = premium. Recommendation: move before market heats up.",
        "[SYNTHETIC] {team}'s {player} has outperformed xStats by significant margin. Sustainable? Our analytics say yes. Grade: A- buy.",
        "[SYNTHETIC] Compared {player} to peers in same age bracket — top 5% in progressive carries and defensive actions. Worth the premium.",
    ],
    'selling_club_fan': [
        "[SYNTHETIC] If we sell {player} now we're set for years. But my heart can't take losing another star. #{team}",
        "[SYNTHETIC] Every World Cup we lose our best players. {player} deserves the big stage but it hurts.",
        "[SYNTHETIC] €{value}M for {player}? That funds the academy for a decade. Accept the bid and reinvest.",
    ],
    'buying_club_fan': [
        "[SYNTHETIC] We need to sign {player} before someone else does. World Cup form is temporary, class is permanent.",
        "[SYNTHETIC] Imagine {player} in our midfield. Make it happen. #TransferWindow",
        "[SYNTHETIC] {player} to {team}? The rumors are heating up. I'm refreshing every 5 minutes.",
    ],
    'agent_source': [
        "[SYNTHETIC] My client {player} is focused on the tournament but several top clubs have expressed interest. Market value now exceeds expectations.",
        "[SYNTHETIC] Contract situation for {player}: 2 years remaining. Release clause activation possible. Multiple clubs monitoring the situation.",
        "[SYNTHETIC] {player} post-tournament market: 5+ clubs inquiring. Expect movement within 10 days. {team} holding firm on valuation.",
    ],
    'beat_reporter': [
        "[SYNTHETIC] BREAKING: {team} set price tag for {player} at €{value}M. Minimum 3 clubs in the race. Story developing.",
        "[SYNTHETIC] Full analysis: {player} World Cup performance reviewed. Transfer implications across Europe's top 5 leagues.",
        "[SYNTHETIC] Sources: {player} camp has not ruled out a move. {team} willing to negotiate. Key meeting set for next week.",
    ],
    'market_analyst': [
        "[SYNTHETIC] {player} market value: pre-tournament €{value}M → post-tournament estimated €{value2}M. That World Cup performance added serious premium.",
        "[SYNTHETIC] Transfer market heat map: {team} players seeing 20-40% value increases. Tournament effect in full force.",
        "[SYNTHETIC] Historical comp: tournament breakouts like {player} typically see 2.5x value appreciation. Market efficiency says buy now.",
    ],
    'rumor_aggregator': [
        "[SYNTHETIC] RUMOR MILL: {player} to Premier League? La Liga? Here's what we're tracking today. Thread 🧵",
        "[SYNTHETIC] {player} transfer saga — all the links in one place. Updated hourly. Bookmark this. #TransferTracker",
        "[SYNTHETIC] The {player} sweepstakes: 8 clubs linked, 3 serious. Here's where things stand right now.",
    ],
    'casual_follower': [
        "[SYNTHETIC] wait {player} might leave {team} now? the world cup really changes everything huh",
        "[SYNTHETIC] Transfer rumor season is exhausting and we're still in the tournament 😅",
        "[SYNTHETIC] all these {player} rumors are wild. just enjoy the football people",
    ],
}


def generate_post(
    driver, agent_id: str, topics: List[Dict],
    recent_posts: List[Dict], round_num: int,
    model_client=None, world_spec: Dict = None, use_llm: bool = True
) -> Optional[Dict]:
    """Generate a transfer/news post for an agent. Every post is tagged [SYNTHETIC].

    ``use_llm`` lets the caller bound how many posts actually hit the cheap model
    (each call is a sequential network round-trip); when False the post is built
    from the template bank only. Template posts still fill {player}/{team}/{value}
    slots from the winner's pack, so they stay on-topic and name real players.
    """
    rng = np.random.default_rng(
        seed=hash(f"{agent_id}_{round_num}") % (2**31)
    )

    with driver.session() as session:
        result = session.run(
            "MATCH (p:Persona {persona_id: $pid}) "
            "RETURN p.archetype AS arch, p.allegiance AS allegiance",
            pid=agent_id
        )
        record = result.single()
        if not record:
            return None
        arch = record['arch']
        allegiance = record['allegiance']

    # Pick a player from winner_stars if available
    stars = (world_spec or {}).get('winner_stars', [])
    player = rng.choice(stars)['name'] if stars else 'Star Player'
    value = str(rng.integers(30, 150))
    value2 = str(rng.integers(40, 200))
    team = world_spec.get('winner_team', allegiance or '??') if world_spec else (allegiance or '??')

    templates = POST_TEMPLATES.get(arch, POST_TEMPLATES['casual_follower'])

    # Fill in template slots
    content = rng.choice(templates)
    content = content.replace('{player}', player)
    content = content.replace('{team}', team)
    content = content.replace('{value}', value)
    content = content.replace('{value2}', value2)

    if model_client and use_llm:
        try:
            star_names = [s['name'] for s in stars][:5] if stars else 'unknown'
            llm_text = llm_chat(
                model_client,
                os.getenv('CHEAP_MODEL', 'gpt-4o-mini'),
                [{
                    "role": "system",
                    "content": (
                        f"You are a football transfer/news persona: {arch}. "
                        f"Winner team: {team}. Key players: {star_names}. "
                        "Write one short post (max 280 chars) about transfer value, "
                        "market movement, or football news related to the World Cup outcome. "
                        "Stay on transfer value and football news topics. "
                        "Do not fabricate real quotes."
                    )
                }],
                max_tokens=120,
                temperature=0.9,
            )
            if llm_text and llm_text.strip():
                content = f"[SYNTHETIC] {llm_text.strip()}"
        except Exception as exc:  # noqa: BLE001 — template fallback, but log it
            _log.warning("cheap-model post generation failed, using template: %s", exc)

    post = {
        'post_id': f"post_{uuid.uuid4().hex[:8]}",
        'agent_id': agent_id,
        'archetype': arch,
        'content': content,
        'round': round_num,
        'synthetic': True,
    }

    with driver.session() as session:
        session.run("""
            MATCH (p:Persona {persona_id: $agent_id})
            CREATE (post:Post {
                post_id: $post_id, content: $content,
                round: $round, synthetic: true
            })
            CREATE (p)-[:POSTED]->(post)
        """, agent_id=agent_id, post_id=post['post_id'],
           content=content, round=round_num)

        if topics:
            topic = rng.choice(topics)
            session.run("""
                MATCH (post:Post {post_id: $post_id})
                MATCH (t:Topic {topic_id: $topic_id})
                MERGE (post)-[:MENTIONS]->(t)
            """, post_id=post['post_id'], topic_id=topic['topic_id'])

    return post


def select_active_agents(
    driver, round_num: int, max_agents: int = 50
) -> List[str]:
    """Select agents to post this round based on response_speed."""
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Persona)
            WHERE rand() < p.response_speed * 0.3
            RETURN p.persona_id AS pid
            LIMIT $max
        """, max=max_agents)
        return [r['pid'] for r in result]


def run_full_simulation(
    driver,
    world_spec: Dict,
    tier: str,
    model_client=None
) -> Dict:
    """Run the full multi-round social simulation.

    Sentiment trajectory is shaped by the world spec — a popular winner
    (e.g. BRA) produces a positive arc; an unexpected winner (underdog)
    produces volatile sentiment with sharp turning points.
    """
    tier_config = {
        'quick': {'rounds': 12, 'agents_per_round': 30},
        'analyst': {'rounds': 24, 'agents_per_round': 80},
        'executive': {'rounds': 40, 'agents_per_round': 150}
    }
    config = tier_config.get(tier, tier_config['quick'])
    n_rounds = config['rounds']

    # Seed sentiment trajectory from world spec
    winner = world_spec.get('winner_team', '??')
    winner_prob = world_spec.get('winner_probability', 0.1)
    packs = world_spec.get('narrative_packs', [])
    audience = world_spec.get('audience_scope', [])

    # Determine sentiment profile — transfer/news framing
    is_underdog = winner_prob < 0.1
    is_popular = winner in ('BRA', 'ARG', 'FRA', 'ENG', 'ESP', 'GER')
    is_host = winner in ('USA', 'MEX', 'CAN')

    # Sentiment: underdog -> more volatile (bigger value-surge buzz)
    if is_underdog:
        base_sentiment = 0.25  # Breakout surprise -> value surge
        drift = 0.015
        volatility = 0.06
    elif is_popular:
        base_sentiment = 0.2   # Expected result, steady transfer buzz
        drift = 0.005
        volatility = 0.03
    elif is_host:
        base_sentiment = 0.15
        drift = 0.008
        volatility = 0.04
    else:
        base_sentiment = 0.1
        drift = 0.01
        volatility = 0.05

    # Keep packs don't influence sentiment (we're transfer/news only)

    with driver.session() as session:
        result = session.run(
            "MATCH (t:Topic) RETURN t.topic_id AS topic_id, t.label AS label"
        )
        topics = [
            {'topic_id': r['topic_id'], 'label': r['label']} for r in result
        ]

    all_posts = []
    sentiment_by_round = []
    rng = np.random.default_rng()

    # Each LLM post is a sequential network round-trip, so an unbounded crowd
    # would make even "quick" tier take many minutes. Cap how many posts hit the
    # cheap model per tier; the rest are built from the (player-filled) template
    # bank. This keeps the report LLM-grounded while bounding latency and cost.
    llm_budget = {'quick': 25, 'analyst': 80, 'executive': 160}.get(tier, 25)
    llm_used = 0

    for round_num in range(n_rounds):
        active_agents = select_active_agents(
            driver, round_num,
            max_agents=config['agents_per_round']
        )

        round_posts = []
        for agent_id in active_agents:
            use_llm = llm_used < llm_budget
            post = generate_post(
                driver, agent_id, topics, round_posts,
                round_num, model_client, world_spec, use_llm=use_llm
            )
            if post:
                if use_llm and model_client and post.get('content', '').strip():
                    llm_used += 1
                round_posts.append(post)

        all_posts.extend(round_posts)

        # Sentiment: base + drift + random walk
        if round_num == 0:
            sentiment = base_sentiment + rng.normal(0, volatility)
        else:
            sentiment = sentiment_by_round[-1] + drift + rng.normal(0, volatility)
        sentiment = max(-1.0, min(1.0, sentiment))
        sentiment_by_round.append(sentiment)

    return {
        'narratives': compile_narrative_clusters(driver, all_posts, world_spec),
        'sentiment': {
            'overall': sentiment_by_round,
            'timestamps': [f"T+{i * 6}h" for i in range(len(sentiment_by_round))]
        },
        'sample_posts': [p for p in all_posts[:20]],
        'turning_points': detect_turning_points(sentiment_by_round),
        'total_posts': len(all_posts),
        'rounds_completed': n_rounds,
        'graph_stats': {
            'nodes': _get_node_count_safe(driver),
            'relations': _get_relation_count_safe(driver)
        },
        'world_context': {
            'winner': winner,
            'winner_probability': winner_prob,
            'is_underdog': is_underdog,
            'is_popular': is_popular,
            'is_host': is_host
        }
    }


def compile_narrative_clusters(driver, posts: List[Dict],
                               world_spec: Dict = None) -> List[Dict]:
    """Group posts into transfer/news narrative clusters."""
    winner = (world_spec or {}).get('winner_team', '??')

    clusters = {
        'value_surge': {
            'label': f'{winner} Player Value Surge',
            'posts': 0,
            'key_terms': ['value', 'release clause', 'premium', 'bargain', 'stock rising'],
        },
        'bidding_war': {
            'label': 'Bidding War Rumors',
            'posts': 0,
            'key_terms': ['bidding war', 'clubs circling', 'race', 'competition', 'sweepstakes'],
        },
        'contract_standoff': {
            'label': 'Contract Standoff',
            'posts': 0,
            'key_terms': ['contract', 'renewal', 'release clause', 'negotiation', 'valuation'],
        },
        'breakout_star': {
            'label': 'Breakout Star Market Impact',
            'posts': 0,
            'key_terms': ['breakout', 'stock rising', 'scout', 'recommendation', 'analytics'],
        },
        'transfer_news_break': {
            'label': 'Breaking Transfer News',
            'posts': 0,
            'key_terms': ['breaking', 'exclusive', 'sources', 'meeting', 'set to'],
        },
    }

    # Assign posts to clusters by full archetype. Posts carry their archetype
    # directly (set in generate_post); we no longer parse it out of the persona
    # id, whose `persona_<archetype>_<i>_<hex>` shape made a naive split collapse
    # most archetypes into one bucket.
    archetype_cluster = {
        'transfer_insider': 'transfer_news_break',
        'beat_reporter': 'transfer_news_break',
        'club_scout': 'breakout_star',
        'market_analyst': 'breakout_star',
        'agent_source': 'contract_standoff',
        'buying_club_fan': 'bidding_war',
        'selling_club_fan': 'bidding_war',
        'rumor_aggregator': 'value_surge',
        'casual_follower': 'value_surge',
    }
    for post in posts:
        arch = post.get('archetype', '')
        cluster_key = archetype_cluster.get(arch, 'value_surge')
        clusters[cluster_key]['posts'] += 1

    total = max(sum(c.get('posts', 0) for c in clusters.values()), 1)

    return [
        {
            'cluster_id': f"cluster_{k}",
            'label': v['label'],
            'agent_count': v.get('posts', 0),
            'dominance': v.get('posts', 0) / total,
            'key_terms': v.get('key_terms', [])
        }
        for k, v in sorted(
            clusters.items(),
            key=lambda x: x[1].get('posts', 0), reverse=True
        )[:5]
    ]


def detect_turning_points(sentiment: List[float]) -> List[Dict]:
    """Detect turning points in sentiment curve."""
    if len(sentiment) < 3:
        return []

    turning_points = []
    for i in range(1, len(sentiment) - 1):
        delta = sentiment[i] - sentiment[i - 1]
        if abs(delta) > 0.08:
            turning_points.append({
                'round': i,
                'direction': 'up' if delta > 0 else 'down',
                'magnitude': abs(delta),
                'sentiment': sentiment[i]
            })

    return sorted(
        turning_points, key=lambda x: x['magnitude'], reverse=True
    )[:5]


def _get_node_count_safe(driver) -> int:
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS cnt")
            record = result.single()
            return record['cnt'] if record else 0
    except Exception:
        return 0


def _get_relation_count_safe(driver) -> int:
    try:
        with driver.session() as session:
            result = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
            record = result.single()
            return record['cnt'] if record else 0
    except Exception:
        return 0
