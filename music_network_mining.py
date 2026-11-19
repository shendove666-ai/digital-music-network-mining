#!/usr/bin/env python3
"""Analyze weighted artist collaborations and export metrics for Gephi.

The real mode reads an edge list and can retain isolates from a verified artist
registry. Simulation mode builds a seeded demonstration with planted hubs and
bridges. Edge weights represent collaboration intensity, and weighted shortest
paths use reciprocal distance.

License: MIT
"""

from __future__ import annotations

import argparse
import csv
import heapq
import logging
import math
import random
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from xml.dom import minidom

try:
    import networkx as nx  # type: ignore
    from networkx.algorithms import community as nx_comm  # type: ignore

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    import pandas as pd  # type: ignore

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MusicNetworkMining")


EMPIRICAL_ARTIST_METADATA: Dict[str, Tuple[str, str]] = {
    # Classical & Neo-Classical (30 Artists)
    "Yo-Yo Ma": ("Classical & Neo-Classical", "Genre Hub"),
    "Ryuichi Sakamoto": ("Classical & Neo-Classical", "Bridge Producer"),
    "Max Richter": ("Classical & Neo-Classical", "Genre Hub"),
    "Ludovico Einaudi": ("Classical & Neo-Classical", "Genre Hub"),
    "Lang Lang": ("Classical & Neo-Classical", "Genre Hub"),
    "Ólafur Arnalds": ("Classical & Neo-Classical", "Bridge Producer"),
    "Nils Frahm": ("Classical & Neo-Classical", "Bridge Producer"),
    "Hildur Guðnadóttir": ("Classical & Neo-Classical", "Artist"),
    "Jóhann Jóhannsson": ("Classical & Neo-Classical", "Artist"),
    "Philip Glass": ("Classical & Neo-Classical", "Genre Hub"),
    "Steve Reich": ("Classical & Neo-Classical", "Artist"),
    "Kronos Quartet": ("Classical & Neo-Classical", "Genre Hub"),
    "Hilary Hahn": ("Classical & Neo-Classical", "Artist"),
    "HAUSER": ("Classical & Neo-Classical", "Artist"),
    "Khatia Buniatishvili": ("Classical & Neo-Classical", "Artist"),
    "Yuja Wang": ("Classical & Neo-Classical", "Artist"),
    "Gustavo Dudamel": ("Classical & Neo-Classical", "Artist"),
    "Itzhak Perlman": ("Classical & Neo-Classical", "Artist"),
    "John Williams": ("Classical & Neo-Classical", "Genre Hub"),
    "Ennio Morricone": ("Classical & Neo-Classical", "Artist"),
    "Joe Hisaishi": ("Classical & Neo-Classical", "Artist"),
    "Tan Dun": ("Classical & Neo-Classical", "Artist"),
    "Hania Rani": ("Classical & Neo-Classical", "Artist"),
    "Víkingur Ólafsson": ("Classical & Neo-Classical", "Artist"),
    "Dustin O'Halloran": ("Classical & Neo-Classical", "Artist"),
    "Hausckha": ("Classical & Neo-Classical", "Artist"),
    "Alice Sara Ott": ("Classical & Neo-Classical", "Artist"),
    "Mari Samuelsen": ("Classical & Neo-Classical", "Artist"),
    "Peter Gregson": ("Classical & Neo-Classical", "Artist"),
    "Gautier Capuçon": ("Classical & Neo-Classical", "Artist"),
    # Electronic & Ambient (30 Artists)
    "Brian Eno": ("Electronic & Ambient", "Bridge Producer"),
    "Hans Zimmer": ("Electronic & Ambient", "Bridge Producer"),
    "Alva Noto": ("Electronic & Ambient", "Artist"),
    "Fennesz": ("Electronic & Ambient", "Artist"),
    "Jon Hopkins": ("Electronic & Ambient", "Genre Hub"),
    "Four Tet": ("Electronic & Ambient", "Genre Hub"),
    "Floating Points": ("Electronic & Ambient", "Bridge Producer"),
    "Aphex Twin": ("Electronic & Ambient", "Artist"),
    "Boards of Canada": ("Electronic & Ambient", "Artist"),
    "Autechre": ("Electronic & Ambient", "Artist"),
    "Bonobo": ("Electronic & Ambient", "Genre Hub"),
    "Kiasmos": ("Electronic & Ambient", "Artist"),
    "Rival Consoles": ("Electronic & Ambient", "Artist"),
    "Christian Löffler": ("Electronic & Ambient", "Artist"),
    "Ben Frost": ("Electronic & Ambient", "Artist"),
    "Tim Hecker": ("Electronic & Ambient", "Artist"),
    "William Basinski": ("Electronic & Ambient", "Artist"),
    "Oneohtrix Point Never": ("Electronic & Ambient", "Bridge Producer"),
    "Arca": ("Electronic & Ambient", "Bridge Producer"),
    "Nicolas Jaar": ("Electronic & Ambient", "Artist"),
    "Moderat": ("Electronic & Ambient", "Artist"),
    "Apparat": ("Electronic & Ambient", "Artist"),
    "Bicep": ("Electronic & Ambient", "Artist"),
    "Caribou": ("Electronic & Ambient", "Artist"),
    "Jamie xx": ("Electronic & Ambient", "Artist"),
    "Disclosure": ("Electronic & Ambient", "Artist"),
    "Flume": ("Electronic & Ambient", "Artist"),
    "Kaytranada": ("Electronic & Ambient", "Bridge Producer"),
    "Flying Lotus": ("Electronic & Ambient", "Bridge Producer"),
    "Squarepusher": ("Electronic & Ambient", "Artist"),
    # Jazz & Fusion (30 Artists)
    "Herbie Hancock": ("Jazz & Fusion", "Genre Hub"),
    "Quincy Jones": ("Jazz & Fusion", "Bridge Producer"),
    "Robert Glasper": ("Jazz & Fusion", "Bridge Producer"),
    "Kamasi Washington": ("Jazz & Fusion", "Genre Hub"),
    "Thundercat": ("Jazz & Fusion", "Bridge Producer"),
    "Chick Corea": ("Jazz & Fusion", "Genre Hub"),
    "Pat Metheny": ("Jazz & Fusion", "Artist"),
    "Wayne Shorter": ("Jazz & Fusion", "Artist"),
    "Esperanza Spalding": ("Jazz & Fusion", "Artist"),
    "Brad Mehldau": ("Jazz & Fusion", "Artist"),
    "Wynton Marsalis": ("Jazz & Fusion", "Artist"),
    "Chris Botti": ("Jazz & Fusion", "Artist"),
    "Diana Krall": ("Jazz & Fusion", "Artist"),
    "Norah Jones": ("Jazz & Fusion", "Artist"),
    "Gregory Porter": ("Jazz & Fusion", "Artist"),
    "Snarky Puppy": ("Jazz & Fusion", "Genre Hub"),
    "Jacob Collier": ("Jazz & Fusion", "Bridge Producer"),
    "Cory Henry": ("Jazz & Fusion", "Artist"),
    "Hiromi": ("Jazz & Fusion", "Artist"),
    "Tigran Hamasyan": ("Jazz & Fusion", "Artist"),
    "Ibrahim Maalouf": ("Jazz & Fusion", "Artist"),
    "Erik Truffaz": ("Jazz & Fusion", "Artist"),
    "Nils Petter Molvær": ("Jazz & Fusion", "Artist"),
    "Pharoah Sanders": ("Jazz & Fusion", "Artist"),
    "Shabaka Hutchings": ("Jazz & Fusion", "Artist"),
    "Yussef Dayes": ("Jazz & Fusion", "Artist"),
    "Tom Misch": ("Jazz & Fusion", "Artist"),
    "Alfa Mist": ("Jazz & Fusion", "Artist"),
    "BADBADNOTGOOD": ("Jazz & Fusion", "Bridge Producer"),
    "Christian Scott aTunde Adjuah": ("Jazz & Fusion", "Artist"),
    # Popular Music (30 Artists)
    "BTS": ("Popular Music", "Genre Hub"),
    "SUGA": ("Popular Music", "Bridge Producer"),
    "RM": ("Popular Music", "Artist"),
    "Jungkook": ("Popular Music", "Artist"),
    "Coldplay": ("Popular Music", "Genre Hub"),
    "Beyoncé": ("Popular Music", "Genre Hub"),
    "Kendrick Lamar": ("Popular Music", "Genre Hub"),
    "The Weeknd": ("Popular Music", "Genre Hub"),
    "Pharrell Williams": ("Popular Music", "Bridge Producer"),
    "Daft Punk": ("Popular Music", "Bridge Producer"),
    "Björk": ("Popular Music", "Bridge Producer"),
    "Radiohead": ("Popular Music", "Genre Hub"),
    "Thom Yorke": ("Popular Music", "Artist"),
    "Jonny Greenwood": ("Popular Music", "Bridge Producer"),
    "David Bowie": ("Popular Music", "Artist"),
    "U2": ("Popular Music", "Artist"),
    "Peter Gabriel": ("Popular Music", "Artist"),
    "Sting": ("Popular Music", "Artist"),
    "Alicia Keys": ("Popular Music", "Artist"),
    "John Legend": ("Popular Music", "Artist"),
    "Anderson .Paak": ("Popular Music", "Bridge Producer"),
    "Bruno Mars": ("Popular Music", "Artist"),
    "Billie Eilish": ("Popular Music", "Artist"),
    "FINNEAS": ("Popular Music", "Bridge Producer"),
    "BLACKPINK": ("Popular Music", "Genre Hub"),
    "IU": ("Popular Music", "Artist"),
    "PSY": ("Popular Music", "Artist"),
    "Epik High": ("Popular Music", "Artist"),
    "Lady Gaga": ("Popular Music", "Artist"),
    "Rosalía": ("Popular Music", "Artist"),
}


class StandaloneGraph:
    """
    Insertion-ordered undirected adjacency for the standalone backend.

    Supports the subset of the NetworkX `nx.Graph` API used by this pipeline. The pipeline
    delegates to `networkx` when installed.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._adj: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def add_node(self, node_id: str, **attr: Any) -> None:
        if node_id not in self._nodes:
            self._nodes[node_id] = {}
            self._adj[node_id] = {}
        self._nodes[node_id].update(attr)

    def add_edge(self, u: str, v: str, **attr: Any) -> None:
        if u not in self._nodes:
            self.add_node(u, label=u, genre="Cross-Genre / Other", role="Artist")
        if v not in self._nodes:
            self.add_node(v, label=v, genre="Cross-Genre / Other", role="Artist")
        if u == v:
            return
        edge_data = dict(attr)
        if "weight" not in edge_data:
            edge_data["weight"] = 1.0
        self._adj[u][v] = edge_data
        self._adj[v][u] = edge_data

    def has_edge(self, u: str, v: str) -> bool:
        return u in self._adj and v in self._adj[u]

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return sum(len(nbrs) for nbrs in self._adj.values()) // 2

    def nodes(self, data: bool = False) -> Any:
        if data:
            return list(self._nodes.items())
        return list(self._nodes.keys())

    @property
    def node_attr_dict(self) -> Dict[str, Dict[str, Any]]:
        return self._nodes

    def edges(self, data: bool = False) -> List[Any]:
        visited_sources: Set[str] = set()
        edges: List[Any] = []
        for source, neighbors in self._adj.items():
            for target, edge_attributes in neighbors.items():
                if target not in visited_sources:
                    if data:
                        edges.append((source, target, edge_attributes))
                    else:
                        edges.append((source, target))
            visited_sources.add(source)
        return edges

    def neighbors(self, u: str) -> List[str]:
        return list(self._adj.get(u, {}).keys())

    def degree(self, u: Optional[str] = None, weight: Optional[str] = None) -> Any:
        if u is not None:
            if weight is None:
                return len(self._adj.get(u, {}))
            return sum(float(d.get(weight, 1.0)) for d in self._adj.get(u, {}).values())
        return {n: self.degree(n, weight=weight) for n in self._nodes}

    def get_edge_data(self, u: str, v: str) -> Dict[str, Any]:
        return self._adj.get(u, {}).get(v, {})


def compute_degree_centrality(G: Any) -> Dict[str, float]:
    """Computes normalized degree centrality C_D(v) = deg(v) / (N - 1)."""
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        return nx.degree_centrality(G)
    n = G.number_of_nodes()
    if n <= 1:
        return {node: 0.0 for node in G.nodes()}
    return {node: G.degree(node) / float(n - 1) for node in G.nodes()}


def compute_closeness_centrality(G: Any) -> Dict[str, float]:
    """
    Computes Wasserman-Faust normalized closeness centrality across connected
    components using unweighted shortest-path distances (BFS).
    """
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        return nx.closeness_centrality(G)
    nodes = G.nodes()
    n = len(nodes)
    closeness: Dict[str, float] = {}
    neighbors = {node: G.neighbors(node) for node in nodes}
    for s in nodes:
        distances: Dict[str, int] = {s: 0}
        queue: List[str] = [s]
        queue_index = 0
        while queue_index < len(queue):
            u = queue[queue_index]
            queue_index += 1
            for v in neighbors[u]:
                if v not in distances:
                    distances[v] = distances[u] + 1
                    queue.append(v)
        distance_sum = sum(distances.values())
        reachable = len(distances) - 1
        if distance_sum > 0 and n > 1:
            node_closeness = (reachable / float(distance_sum)) * (reachable / float(n - 1))
        else:
            node_closeness = 0.0
        closeness[s] = node_closeness
    return closeness


def compute_betweenness_centrality(G: Any, weight: str = "weight") -> Dict[str, float]:
    """
    Normalized betweenness using Brandes' algorithm.

    The stored edge attribute is collaboration intensity, so a larger value is a
    stronger tie. Shortest paths use distance = 1 / intensity. Constraint,
    effective size, and Louvain modularity still read the original intensity.
    """
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        distance_graph = G.copy()
        for u, v, data in distance_graph.edges(data=True):
            strength = float(data.get(weight, 1.0))
            data["distance"] = 1.0 / strength if strength > 0.0 else 1.0
        return nx.betweenness_centrality(distance_graph, weight="distance", normalized=True)

    nodes = G.nodes()
    n = len(nodes)
    betweenness: Dict[str, float] = {v: 0.0 for v in nodes}
    if n <= 2:
        return betweenness

    weighted_neighbors: Dict[str, List[Tuple[str, float]]] = {}
    for node in nodes:
        weighted_neighbors[node] = []
        for neighbor in G.neighbors(node):
            strength = float(G.get_edge_data(node, neighbor).get(weight, 1.0))
            edge_distance = 1.0 / strength if strength > 0.0 else 1.0
            weighted_neighbors[node].append((neighbor, edge_distance))

    for s in nodes:
        settled_order: List[str] = []
        predecessors: Dict[str, List[str]] = {w: [] for w in nodes}
        sigma: Dict[str, float] = {w: 0.0 for w in nodes}
        sigma[s] = 1.0
        settled_distances: Dict[str, float] = {}
        settled_distances[s] = 0.0
        heap: List[Tuple[float, int, str, str]] = []
        counter = 0
        heapq.heappush(heap, (0.0, counter, s, s))
        tentative_distances: Dict[str, float] = {s: 0.0}

        while heap:
            distance, _, predecessor, v = heapq.heappop(heap)
            if v in settled_distances and v != s:
                continue
            sigma[v] += sigma[predecessor] if v != s else 0.0
            settled_order.append(v)
            settled_distances[v] = distance
            for w, edge_distance in weighted_neighbors[v]:
                candidate_distance = distance + edge_distance
                if w not in settled_distances and (w not in tentative_distances or candidate_distance < tentative_distances[w] - 1e-12):
                    tentative_distances[w] = candidate_distance
                    counter += 1
                    heapq.heappush(heap, (candidate_distance, counter, v, w))
                    sigma[w] = 0.0
                    predecessors[w] = [v]
                elif w not in settled_distances and abs(candidate_distance - tentative_distances.get(w, -1.0)) <= 1e-12:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        dependency: Dict[str, float] = {w: 0.0 for w in nodes}
        while settled_order:
            w = settled_order.pop()
            dependency_scale = (1.0 + dependency[w]) / sigma[w] if sigma[w] > 0 else 0.0
            for v in predecessors[w]:
                dependency[v] += sigma[v] * dependency_scale
            if w != s:
                betweenness[w] += dependency[w]

    scale = 1.0 / ((n - 1) * (n - 2))
    for v in betweenness:
        betweenness[v] *= scale
    return betweenness


def compute_clustering_coefficient(G: Any) -> Dict[str, float]:
    """Computes local unweighted clustering coefficient C(v) = 2*T(v) / (k_v*(k_v-1))."""
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        return nx.clustering(G)
    clustering: Dict[str, float] = {}
    neighbors = {node: set(G.neighbors(node)) for node in G.nodes()}
    for ego, ego_neighbors in neighbors.items():
        degree = len(ego_neighbors)
        if degree < 2:
            clustering[ego] = 0.0
            continue
        triangles = 0
        for alter in ego_neighbors:
            # Count each linked pair among the ego's neighbors once.
            for other in ego_neighbors.intersection(neighbors[alter]):
                if other > alter:
                    triangles += 1
        clustering[ego] = (2.0 * triangles) / float(degree * (degree - 1))
    return clustering


def compute_burt_structural_holes(
    G: Any, weight: str = "weight"
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Computes Ronald Burt's (1992) Structural Holes metrics:
    1. Network Constraint C_i = sum_j (p_ij + sum_q p_iq * p_qj)^2
       Lower constraint indicates an actor spanning rich structural holes
       (higher brokerage capacity across disconnected social worlds).
    2. Effective Size ES_i = sum_j [1 - sum_q p_iq * m_jq]
       Quantifies the non-redundant portion of an actor's ego network.
    """
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        raw_constraint = nx.constraint(G, weight=weight)
        raw_effective_size = nx.effective_size(G, weight=weight)
        constraint_clean = {
            k: (0.0 if (v is None or math.isnan(v)) else float(v))
            for k, v in raw_constraint.items()
        }
        eff_size_clean = {
            k: (0.0 if (v is None or math.isnan(v)) else float(v))
            for k, v in raw_effective_size.items()
        }
        return constraint_clean, eff_size_clean

    nodes = G.nodes()
    # p scales each tie by total ego strength, and m scales it by the strongest tie.
    neighbors = {node: G.neighbors(node) for node in nodes}
    p: Dict[str, Dict[str, float]] = {}
    m: Dict[str, Dict[str, float]] = {}
    for u in nodes:
        ego_neighbors = neighbors[u]
        if not ego_neighbors:
            p[u] = {}
            m[u] = {}
            continue
        weights = {v: float(G.get_edge_data(u, v).get(weight, 1.0)) for v in ego_neighbors}
        ego_total_strength = sum(weights.values())
        ego_max_strength = max(weights.values())
        p[u] = {v: (w / ego_total_strength if ego_total_strength > 0 else 0.0) for v, w in weights.items()}
        m[u] = {v: (w / ego_max_strength if ego_max_strength > 0 else 0.0) for v, w in weights.items()}

    constraint: Dict[str, float] = {}
    effective_size: Dict[str, float] = {}

    for i in nodes:
        ego_neighbors = neighbors[i]
        if not ego_neighbors:
            constraint[i] = 0.0
            effective_size[i] = 0.0
            continue

        ego_proportions = p[i]
        ego_constraint = 0.0
        for j in ego_neighbors:
            direct = ego_proportions.get(j, 0.0)
            indirect = 0.0
            for q in ego_neighbors:
                if q != i and q != j:
                    indirect += ego_proportions.get(q, 0.0) * p[q].get(j, 0.0)
            ego_constraint += (direct + indirect) ** 2
        constraint[i] = ego_constraint

        ego_effective_size = 0.0
        for j in ego_neighbors:
            redundancy = 0.0
            for q in ego_neighbors:
                if q != i and q != j:
                    redundancy += ego_proportions.get(q, 0.0) * m[j].get(q, 0.0)
            ego_effective_size += 1.0 - redundancy
        effective_size[i] = ego_effective_size

    return constraint, effective_size


def detect_louvain_communities(
    G: Any, weight: str = "weight", seed: int = 42
) -> Tuple[Dict[str, int], float]:
    """
    Return weighted Louvain community IDs and Newman-Girvan modularity.

    Communities are inferred from the weighted graph. Genre metadata do not
    enter the objective.
    """
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        communities = nx_comm.louvain_communities(G, weight=weight, seed=seed)
        modularity_q = nx_comm.modularity(G, communities, weight=weight)
        # Stable IDs follow community size, then the smallest node ID.
        ordered_communities = sorted(communities, key=lambda members: (-len(members), min(members)))
        node_to_community: Dict[str, int] = {}
        for comm_id, community_members in enumerate(ordered_communities):
            for node in community_members:
                node_to_community[node] = comm_id
        return node_to_community, float(modularity_q)

    # Two-phase hierarchical Louvain modularity optimization (Blondel et al., 2008)
    rng = random.Random(seed)
    nodes = list(G.nodes())
    if not nodes:
        return {}, 0.0

    weighted_edges = list(G.edges(data=True))
    total_edge_weight = sum(float(edge_attributes.get(weight, 1.0)) for _, _, edge_attributes in weighted_edges)
    if total_edge_weight <= 0:
        return {n: 0 for n in nodes}, 0.0

    node_strength: Dict[str, float] = {u: float(G.degree(u, weight=weight)) for u in nodes}
    weighted_adjacency: Dict[str, Dict[str, float]] = {u: {} for u in nodes}
    for u, v, edge_attributes in weighted_edges:
        w = float(edge_attributes.get(weight, 1.0))
        weighted_adjacency[u][v] = weighted_adjacency[u].get(v, 0.0) + w
        weighted_adjacency[v][u] = weighted_adjacency[v].get(u, 0.0) + w

    node_to_community: Dict[str, int] = {u: idx for idx, u in enumerate(nodes)}

    while True:
        supernodes = sorted(list(set(node_to_community.values())))
        supernode_neighbors: Dict[int, Dict[int, float]] = {c: {} for c in supernodes}
        internal_weight_twice: Dict[int, float] = {c: 0.0 for c in supernodes}
        for u in nodes:
            cu = node_to_community[u]
            for v, w in weighted_adjacency[u].items():
                cv = node_to_community[v]
                if cu == cv:
                    internal_weight_twice[cu] += w
                else:
                    supernode_neighbors[cu][cv] = supernode_neighbors[cu].get(cv, 0.0) + w

        supernode_strength = {c: internal_weight_twice[c] + sum(supernode_neighbors[c].values()) for c in supernodes}
        supernode_to_community = {c: c for c in supernodes}
        community_total_strength = {c: supernode_strength[c] for c in supernodes}

        improved = False
        local_moved = True
        passes = 0
        while local_moved and passes < 50:
            local_moved = False
            passes += 1
            order = list(supernodes)
            rng.shuffle(order)
            for supernode in order:
                old_community = supernode_to_community[supernode]
                moving_strength = supernode_strength[supernode]
                community_total_strength[old_community] -= moving_strength

                weight_by_candidate_community: Dict[int, float] = {}
                for nbr, w in supernode_neighbors[supernode].items():
                    neighbor_community = supernode_to_community[nbr]
                    weight_by_candidate_community[neighbor_community] = weight_by_candidate_community.get(neighbor_community, 0.0) + w

                best_community = old_community
                old_internal_weight = weight_by_candidate_community.get(old_community, 0.0)
                base_gain = old_internal_weight - (community_total_strength.get(old_community, 0.0) * moving_strength) / (2.0 * total_edge_weight)
                best_delta = 0.0

                for candidate_community, candidate_internal_weight in weight_by_candidate_community.items():
                    gain = (candidate_internal_weight - (community_total_strength.get(candidate_community, 0.0) * moving_strength) / (2.0 * total_edge_weight)) - base_gain
                    if gain > best_delta + 1e-10:
                        best_delta = gain
                        best_community = candidate_community

                supernode_to_community[supernode] = best_community
                community_total_strength[best_community] = community_total_strength.get(best_community, 0.0) + moving_strength
                if best_community != old_community:
                    local_moved = True
                    improved = True

        for u in nodes:
            node_to_community[u] = supernode_to_community[node_to_community[u]]

        if not improved or len(set(node_to_community.values())) == len(supernodes):
            break

    community_groups: Dict[int, List[str]] = {}
    for u, cid in node_to_community.items():
        community_groups.setdefault(cid, []).append(u)

    sorted_groups = sorted(
        community_groups.values(), key=lambda members: (-len(members), min(members))
    )
    final_map: Dict[str, int] = {}
    for new_id, group in enumerate(sorted_groups):
        for u in group:
            final_map[u] = new_id

    modularity = 0.0
    for group in sorted_groups:
        group_set = set(group)
        community_internal_weight = 0.0
        community_strength = 0.0
        for u in group:
            community_strength += node_strength[u]
            for v, w in weighted_adjacency[u].items():
                if v in group_set:
                    community_internal_weight += w
        community_internal_weight /= 2.0
        modularity += (community_internal_weight / total_edge_weight) - ((community_strength / (2.0 * total_edge_weight)) ** 2)

    return final_map, float(modularity)


def write_gephi_gexf(G: Any, output_path: str) -> None:
    """
    Export graph topology and typed attributes for Gephi.

    The standalone schema includes `Modularity_Class` (integer/partition) and centrality/structural
    hole metrics (float/ranking).
    """
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        nx.write_gexf(G, output_path)
        return

    gexf = ET.Element(
        "gexf",
        {
            "xmlns": "http://www.gexf.net/1.2draft",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.gexf.net/1.2draft http://www.gexf.net/1.2draft/gexf.xsd",
            "version": "1.2",
        },
    )
    meta = ET.SubElement(
        gexf,
        "meta",
        {"lastmodifieddate": datetime.utcnow().strftime("%Y-%m-%d")},
    )
    ET.SubElement(meta, "creator").text = "Digital Music Network Mining Pipeline v2.0"
    ET.SubElement(meta, "description").text = (
        "Cross-Genre Artist Collaboration Network with Louvain Modularity and Burt Structural Holes"
    )

    graph_el = ET.SubElement(
        gexf,
        "graph",
        {"mode": "static", "defaultedgetype": "undirected"},
    )

    node_attrs_schema = [
        ("0", "genre", "string"),
        ("1", "role", "string"),
        ("2", "Modularity_Class", "integer"),
        ("3", "Degree", "integer"),
        ("4", "Degree_Centrality", "double"),
        ("5", "Betweenness_Centrality", "double"),
        ("6", "Closeness_Centrality", "double"),
        ("7", "Clustering_Coefficient", "double"),
        ("8", "Constraint", "double"),
        ("9", "Effective_Size", "double"),
    ]
    attrs_node_el = ET.SubElement(
        graph_el, "attributes", {"class": "node", "mode": "static"}
    )
    for attr_id, title, attr_type in node_attrs_schema:
        ET.SubElement(
            attrs_node_el,
            "attribute",
            {"id": attr_id, "title": title, "type": attr_type},
        )

    attrs_edge_el = ET.SubElement(
        graph_el, "attributes", {"class": "edge", "mode": "static"}
    )
    ET.SubElement(
        attrs_edge_el,
        "attribute",
        {"id": "0", "title": "relation", "type": "string"},
    )

    nodes_el = ET.SubElement(graph_el, "nodes")
    for node_id, source_attributes in G.nodes(data=True):
        node_el = ET.SubElement(
            nodes_el,
            "node",
            {"id": str(node_id), "label": str(source_attributes.get("label", node_id))},
        )
        attvalues_el = ET.SubElement(node_el, "attvalues")
        for attr_id, title, _ in node_attrs_schema:
            attribute_value = source_attributes.get(title, "")
            ET.SubElement(
                attvalues_el,
                "attvalue",
                {"for": attr_id, "value": str(attribute_value)},
            )

    edges_el = ET.SubElement(graph_el, "edges")
    for edge_index, (u, v, edge_attributes) in enumerate(G.edges(data=True)):
        w = edge_attributes.get("weight", 1.0)
        rel = edge_attributes.get("relation", "Collaboration")
        edge_el = ET.SubElement(
            edges_el,
            "edge",
            {
                "id": str(edge_index),
                "source": str(u),
                "target": str(v),
                "weight": str(w),
            },
        )
        e_attvalues = ET.SubElement(edge_el, "attvalues")
        ET.SubElement(
            e_attvalues,
            "attvalue",
            {"for": "0", "value": str(rel)},
        )

    raw_xml = ET.tostring(gexf, encoding="utf-8")
    parsed_xml = minidom.parseString(raw_xml)
    pretty_xml = parsed_xml.toprettyxml(indent="  ", encoding="utf-8")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(pretty_xml)


def build_simulation_benchmark_network(seed: int = 42) -> Any:
    """Build a seeded 120-node example with planted genre hubs and bridges."""
    random.seed(seed)
    G = nx.Graph() if HAS_NETWORKX else StandaloneGraph()

    genre_configs = {
        "Classical & Neo-Classical": {"prefix": "CLS", "count": 28},
        "Popular Music": {"prefix": "POP", "count": 32},
        "Jazz & Fusion": {"prefix": "JAZ", "count": 26},
        "Electronic & Ambient": {"prefix": "ELC", "count": 26},
    }

    genre_rosters: Dict[str, List[str]] = {}

    for genre, genre_config in genre_configs.items():
        genre_artists: List[str] = []
        for i in range(1, int(genre_config["count"]) + 1):
            node_id = f"{genre_config['prefix']}_Artist_{i:02d}"
            role = "Genre Hub" if i <= 2 else "Artist"
            G.add_node(node_id, label=node_id, genre=genre, role=role)
            genre_artists.append(node_id)
        genre_rosters[genre] = genre_artists

    bridge_nodes: List[str] = []
    for i in range(1, 9):
        bridge_id = f"BRIDGE_Producer_{i:02d}"
        G.add_node(
            bridge_id,
            label=bridge_id,
            genre="Cross-Genre Producer",
            role="Bridge Producer",
        )
        bridge_nodes.append(bridge_id)

    # Hubs receive extra sampled ties before remaining within-genre pairs are tried.
    for genre, genre_artists in genre_rosters.items():
        hubs = genre_artists[:2]
        non_hub_artists = genre_artists[2:]

        for hub in hubs:
            partners = random.sample(non_hub_artists, k=int(len(non_hub_artists) * 0.55))
            for partner in partners:
                G.add_edge(
                    hub,
                    partner,
                    weight=random.randint(2, 6),
                    relation="Intra-Genre Collab",
                )

        for i in range(len(genre_artists)):
            for j in range(i + 1, len(genre_artists)):
                if not G.has_edge(genre_artists[i], genre_artists[j]) and random.random() < 0.14:
                    G.add_edge(
                        genre_artists[i],
                        genre_artists[j],
                        weight=random.randint(1, 3),
                        relation="Intra-Genre Collab",
                    )

    # Each planted bridge samples partners from three genres.
    genre_list = list(genre_rosters.keys())
    for bridge in bridge_nodes:
        connected_genres = random.sample(genre_list, k=3)
        for partner_genre in connected_genres:
            bridge_partners = random.sample(genre_rosters[partner_genre], k=random.randint(3, 5))
            for target in bridge_partners:
                G.add_edge(
                    bridge,
                    target,
                    weight=random.randint(2, 5),
                    relation="Cross-Genre Collab",
                )

    # Repeated attempts can target the same unordered artist pair.
    all_regular_nodes = [n for genre_artists in genre_rosters.values() for n in genre_artists]
    for _ in range(18):
        u, v = random.sample(all_regular_nodes, 2)
        u_genre = G.nodes[u]["genre"] if HAS_NETWORKX else G.node_attr_dict[u]["genre"]
        v_genre = G.nodes[v]["genre"] if HAS_NETWORKX else G.node_attr_dict[v]["genre"]
        if u_genre != v_genre:
            G.add_edge(u, v, weight=1, relation="Cross-Genre Collab")

    return G


def _load_registry_metadata(
    artist_registry_path: str,
) -> Tuple[Dict[str, Tuple[str, str]], List[str]]:
    """Return metadata and roster names from a manually confirmed registry.

    MusicBrainz may use a canonical display name that differs from the legacy
    name used in the original exploratory sample (for example, ``坂本龍一`` and
    ``Ryuichi Sakamoto``).  The registry provides an explicit, reviewable link
    between those names.  It is used only for display metadata; it never
    changes the MusicBrainz IDs or recording-level evidence.
    """
    registry_file = Path(artist_registry_path)
    if not registry_file.exists():
        raise FileNotFoundError(
            f"Artist registry not found at '{artist_registry_path}'."
        )

    with registry_file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required_cols = {
            "legacy_name", "canonical_name", "confirmation_status",
        }
        if reader.fieldnames is None or not required_cols.issubset(reader.fieldnames):
            raise ValueError(
                f"Invalid artist registry schema in {artist_registry_path}. "
                f"Expected columns: {sorted(required_cols)}"
            )

        metadata: Dict[str, Tuple[str, str]] = {}
        roster: List[str] = []
        for line_number, identity_row in enumerate(reader, start=2):
            status = identity_row["confirmation_status"].strip().casefold()
            if status != "confirmed":
                continue
            legacy_name = identity_row["legacy_name"].strip()
            canonical_name = identity_row["canonical_name"].strip()
            if not legacy_name or not canonical_name:
                raise ValueError(
                    f"Confirmed registry row {line_number} needs legacy_name and canonical_name."
                )
            if canonical_name in metadata:
                raise ValueError(
                    f"Duplicate confirmed canonical_name in registry: {canonical_name}"
                )
            metadata[canonical_name] = EMPIRICAL_ARTIST_METADATA.get(
                legacy_name, ("Cross-Genre / Other", "Artist")
            )
            roster.append(canonical_name)

    if not roster:
        raise ValueError(
            f"Artist registry '{artist_registry_path}' has no confirmed artists."
        )
    return metadata, roster


def load_empirical_artist_network(
    edgelist_path: str, artist_registry_path: Optional[str] = None
) -> Any:
    """
    Constructs a cross-genre collaboration network from an empirical CSV edge
    list (``Source,Target,Weight,Relation_Type``) and enriches nodes with
    genre and role classifications.  When a confirmed MusicBrainz registry is
    supplied, all confirmed artists are included, including artists with no
    verified co-credit in the retrieved data.

    Parameters:
        edgelist_path (str): Path to the empirical CSV file.
        artist_registry_path (str | None): Optional manually confirmed
            MusicBrainz registry used for canonical-name metadata and isolates.

    Returns:
        Graph: Populated undirected weighted empirical collaboration network.
    """
    edge_file = Path(edgelist_path)
    if not edge_file.exists():
        raise FileNotFoundError(
            f"Empirical edge list not found at '{edgelist_path}'. "
            "Verify that 'data/real_artist_edgelist.csv' exists."
        )

    G = nx.Graph() if HAS_NETWORKX else StandaloneGraph()
    registry_metadata: Dict[str, Tuple[str, str]] = {}
    confirmed_roster: List[str] = []
    if artist_registry_path:
        registry_metadata, confirmed_roster = _load_registry_metadata(
            artist_registry_path
        )

    def metadata_for(artist: str) -> Tuple[str, str]:
        return registry_metadata.get(
            artist,
            EMPIRICAL_ARTIST_METADATA.get(artist, ("Cross-Genre / Other", "Artist")),
        )

    with open(edge_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required_cols = {"Source", "Target", "Weight", "Relation_Type"}
        if reader.fieldnames is None or not required_cols.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Invalid CSV schema in {edgelist_path}. "
                f"Expected columns: {sorted(list(required_cols))}"
            )

        for line_number, edge_row in enumerate(reader, start=2):
            u = edge_row["Source"].strip()
            v = edge_row["Target"].strip()
            if not u or not v or u == v:
                continue
            try:
                weight = float(edge_row["Weight"])
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid weight on line %d (%s -> %s); defaulting to 1.0",
                    line_number,
                    u,
                    v,
                )
                weight = 1.0
            relation_type = edge_row["Relation_Type"].strip() or "Cross-Genre Collab"

            for artist in (u, v):
                genre, role = metadata_for(artist)
                G.add_node(artist, label=artist, genre=genre, role=role)

            G.add_edge(
                u,
                v,
                weight=int(weight) if weight.is_integer() else weight,
                relation=relation_type,
            )

    for artist in confirmed_roster:
        genre, role = metadata_for(artist)
        G.add_node(artist, label=artist, genre=genre, role=role)

    return G


def analyze_and_export_network(
    G: Any,
    mode: str,
    gexf_path: str = "music_network_advanced.gexf",
    csv_path: str = "music_network_metrics_v2.csv",
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Export node metrics in graph order and return a separately ranked list."""
    logger.info("Initializing Complex Network & Structural Holes Analysis (mode='%s')", mode)

    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()

    degree_scores = compute_degree_centrality(G)
    betweenness_scores = compute_betweenness_centrality(G, weight="weight")
    closeness_scores = compute_closeness_centrality(G)
    clustering_scores = compute_clustering_coefficient(G)
    avg_clustering = (
        sum(clustering_scores.values()) / float(num_nodes) if num_nodes > 0 else 0.0
    )

    modularity_map, modularity_q = detect_louvain_communities(
        G, weight="weight", seed=seed
    )
    num_communities = len(set(modularity_map.values()))

    constraint_map, effective_size_map = compute_burt_structural_holes(
        G, weight="weight"
    )

    metric_rows: List[Dict[str, Any]] = []
    for node_id, source_attributes in G.nodes(data=True):
        degree = int(G.degree(node_id))
        degree_centrality = round(float(degree_scores.get(node_id, 0.0)), 4)
        betweenness_centrality = round(float(betweenness_scores.get(node_id, 0.0)), 4)
        closeness_centrality = round(float(closeness_scores.get(node_id, 0.0)), 4)
        clustering = round(float(clustering_scores.get(node_id, 0.0)), 4)
        community_id = int(modularity_map.get(node_id, 0))
        constraint = round(float(constraint_map.get(node_id, 0.0)), 4)
        effective_size = round(float(effective_size_map.get(node_id, 0.0)), 4)

        node_attributes = G.nodes[node_id] if HAS_NETWORKX else G.node_attr_dict[node_id]
        node_attributes["Degree"] = degree
        node_attributes["Degree_Centrality"] = degree_centrality
        node_attributes["Betweenness_Centrality"] = betweenness_centrality
        node_attributes["Closeness_Centrality"] = closeness_centrality
        node_attributes["Clustering_Coefficient"] = clustering
        node_attributes["Modularity_Class"] = community_id
        node_attributes["Constraint"] = constraint
        node_attributes["Effective_Size"] = effective_size

        metric_rows.append(
            {
                "Artist_ID": node_id,
                "Genre_Group": source_attributes.get("genre", "Unknown"),
                "Role": source_attributes.get("role", "Artist"),
                "Degree": degree,
                "Degree_Centrality": degree_centrality,
                "Betweenness_Centrality": betweenness_centrality,
                "Closeness_Centrality": closeness_centrality,
                "Clustering_Coefficient": clustering,
                "Modularity_Class": community_id,
                "Constraint": constraint,
                "Effective_Size": effective_size,
            }
        )

    # Rank by rounded betweenness, effective size, then degree. Exact ties keep node order.
    ranked_rows = sorted(
        metric_rows,
        key=lambda row: (row["Betweenness_Centrality"], row["Effective_Size"], row["Degree"]),
        reverse=True,
    )

    write_gephi_gexf(G, gexf_path)
    logger.info("Exported Gephi topology file with node attributes: %s", gexf_path)

    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "Artist_ID",
        "Genre_Group",
        "Role",
        "Degree",
        "Degree_Centrality",
        "Betweenness_Centrality",
        "Closeness_Centrality",
        "Clustering_Coefficient",
        "Modularity_Class",
        "Constraint",
        "Effective_Size",
    ]
    if HAS_PANDAS:
        metric_frame = pd.DataFrame(metric_rows)
        metric_frame.to_csv(csv_path, index=False, encoding="utf-8")
    else:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(metric_rows)
    logger.info("Exported full sociological node metrics table: %s", csv_path)

    print("\n" + "=" * 88)
    print(f"COMPLEX NETWORK TOPOLOGY & STRUCTURAL HOLES SUMMARY [MODE: {mode.upper()}]")
    print("=" * 88)
    print(f"Total Artist Nodes (|V|)             : {num_nodes}")
    print(f"Total Collaboration Edges (|E|)      : {num_edges}")
    density = (2.0 * num_edges) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0.0
    print(f"Graph Density                        : {density:.4f}")
    print(f"Average Clustering Coefficient       : {avg_clustering:.4f}")
    print(f"Louvain Detected Communities         : {num_communities}")
    print(f"Global Newman-Girvan Modularity (Q)  : {modularity_q:.4f}")
    print("-" * 88)

    _print_top_table(
        title="TOP 5 DEGREE CENTRALITY NODES (Intra-Community Prolific Hubs)",
        rows=_top_five(metric_rows, key=lambda row: row["Degree_Centrality"], descending=True),
    )
    _print_top_table(
        title="TOP 5 BETWEENNESS CENTRALITY NODES (Cross-Genre Shortest-Path Brokers)",
        rows=_top_five(
            metric_rows, key=lambda row: row["Betweenness_Centrality"], descending=True
        ),
    )
    _print_top_table(
        title="TOP 5 STRUCTURAL HOLE SPANNERS (Lowest Burt Constraint & High Effective Size)",
        rows=_top_five(
            [row for row in metric_rows if row["Degree"] >= 3],
            key=lambda row: (row["Constraint"], -row["Effective_Size"]),
        ),
    )
    print("=" * 88 + "\n")

    return ranked_rows


def _top_five(
    rows: List[Dict[str, Any]],
    key: Callable[[Dict[str, Any]], float | Tuple[float, ...]],
    descending: bool = False,
) -> List[Dict[str, Any]]:
    for row in rows:
        rank = key(row)
        scores = rank if isinstance(rank, tuple) else (rank,)
        if any(not math.isfinite(score) for score in scores):
            # NaN keys are not totally ordered. Keep the original sort in this case.
            return sorted(rows, key=key, reverse=descending)[:5]
    select = heapq.nlargest if descending else heapq.nsmallest
    return select(5, rows, key=key)


def _print_top_table(title: str, rows: List[Dict[str, Any]]) -> None:
    """Formats and prints a clean ASCII academic comparison table to stdout."""
    print(f"\n>>> {title}")
    header = (
        f"{'Artist_ID':<24} | {'Genre_Group':<25} | {'Deg':>3} | "
        f"{'Betw':>6} | {'Mod':>3} | {'Constr':>6} | {'EffSize':>7}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{str(row['Artist_ID'])[:24]:<24} | "
            f"{str(row['Genre_Group'])[:25]:<25} | "
            f"{row['Degree']:>3d} | "
            f"{row['Betweenness_Centrality']:>6.4f} | "
            f"{row['Modularity_Class']:>3d} | "
            f"{row['Constraint']:>6.4f} | "
            f"{row['Effective_Size']:>7.4f}"
        )


def main(
    mode: str = "real",
    edgelist_path: str = "data/real_artist_edgelist.csv",
    artist_registry_path: Optional[str] = None,
    gexf_output: str = "music_network_advanced.gexf",
    csv_output: str = "music_network_metrics_v2.csv",
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Run the analysis on a seeded demonstration (`mode='simulation'`) or a supplied edge list (`mode='real'`).

    Parameters:
        mode (str): Execution mode ('real' or 'simulation').
        edgelist_path (str): Path to empirical edge list CSV when mode='real'.
        artist_registry_path (str | None): Optional confirmed MusicBrainz
            registry used when mode='real'.
        gexf_output (str): Output file path for the Gephi .gexf network file.
        csv_output (str): Output file path for the v2 node metrics CSV table.
        seed (int): Random seed for reproducibility.

    Returns:
        List[Dict[str, Any]]: Computed node-level network metrics.
    """
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"real", "simulation"}:
        raise ValueError(
            f"Unsupported pipeline mode '{mode}'. Choose 'real' or 'simulation'."
        )

    if normalized_mode == "simulation":
        logger.info("Executing Generative Simulation Benchmark Pipeline (N=120)...")
        graph = build_simulation_benchmark_network(seed=seed)
    else:
        logger.info("Executing Empirical Streaming Collaboration Pipeline from '%s'...", edgelist_path)
        graph = load_empirical_artist_network(
            edgelist_path=edgelist_path,
            artist_registry_path=artist_registry_path,
        )

    return analyze_and_export_network(
        G=graph,
        mode=normalized_mode,
        gexf_path=gexf_output,
        csv_path=csv_output,
        seed=seed,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Digital Music Community & Cross-Genre Artist Collaboration Network Mining "
            "(Dual-Pipeline Complex Network & Structural Holes Analyzer)"
        )
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="real",
        choices=["real", "simulation"],
        help="Execution pipeline mode: 'real' (empirical CSV dataset) or 'simulation' (synthetic benchmark).",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/real_artist_edgelist.csv",
        help="Path to the empirical edge list CSV file (used when --mode=real).",
    )
    parser.add_argument(
        "--artist-registry",
        type=str,
        default=None,
        help=(
            "Optional confirmed MusicBrainz artist registry. Its confirmed "
            "artists are included as nodes, even when they have no verified edge."
        ),
    )
    parser.add_argument(
        "--gexf",
        type=str,
        default="music_network_advanced.gexf",
        help="Output path for the enriched Gephi GEXF topology file.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="music_network_metrics_v2.csv",
        help="Output path for the enriched node metrics CSV file.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for generative benchmark and Louvain community detection.",
    )
    args = parser.parse_args()

    try:
        main(
            mode=args.mode,
            edgelist_path=args.input,
            artist_registry_path=args.artist_registry,
            gexf_output=args.gexf,
            csv_output=args.csv,
            seed=args.seed,
        )
    except Exception as exc:
        logger.error("Pipeline execution terminated with error: %s", exc)
        sys.exit(1)
