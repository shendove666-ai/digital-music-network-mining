#!/usr/bin/env python3
"""
music_network_mining.py
===============================================================================
Digital Music Community & Cross-Genre Artist Collaboration Network Mining
via Complex Network Theory and Computational Social Science
===============================================================================

Author: Portfolio Project for MSc in Social Computing Application (XJTLU)
License: MIT

Description:
    An enterprise-grade graph mining and computational social science framework
    designed to analyze intra-community cohesion and cross-genre brokerage in
    digital music collaboration ecosystems.

    Key Architectural Features:
    1. Dual-Pipeline Execution Engine (`mode='simulation'` vs. `mode='real'`):
       - Simulation Mode: Generates a parameterized 120-node synthetic benchmark
         exhibiting small-world clustering and scale-free hub attachment across
         four musical macro-genres and eight dedicated cross-genre bridge nodes.
       - Empirical Mode: Parses curated real-world artist collaboration records
         from `data/real_artist_edgelist.csv` (120 recording artists, 260
         hand-curated links without album citations).
    2. Computational Social Science & Complex Network Metrics:
       - Classical Centralities: Degree, Normalized Degree Centrality,
         Weighted Betweenness Centrality, and Closeness Centrality.
       - Local Transitivity: Unweighted and Weighted Clustering Coefficients.
       - Community Structure: Blondel et al.'s Louvain Modularity Optimization
         (`Modularity_Class` assignment and global Modularity Q evaluation).
       - Ronald Burt's Structural Holes Theory: Network Constraint (`nx.constraint`)
         and Non-Redundant Effective Size (`nx.effective_size`) to quantify
         inter-genre brokerage capital and information arbitrage advantages.
    3. Gephi-Ready Export Interface:
       - Exports `music_network_metrics_v2.csv` for statistical verification.
       - Exports `music_network_advanced.gexf` (GEXF 1.2 specification) with
         strongly typed node and edge attributes for direct visual mapping
         in Gephi (ForceAtlas2 / Yifan Hu layouts).
"""

from __future__ import annotations

import argparse
import csv
import heapq
import logging
import math
import os
import random
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from xml.dom import minidom

# Attempt standard scientific library imports with clean fallback support
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


# ==============================================================================
# Logging Configuration
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MusicNetworkMining")


# ==============================================================================
# Empirical Artist Metadata Registry (Used in 'real' Pipeline Mode)
# ==============================================================================
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


# ==============================================================================
# Lightweight Undirected Weighted Graph Abstraction (NetworkX-Compatible)
# ==============================================================================
class StandaloneGraph:
    """
    A self-contained undirected weighted graph data structure mirroring the
    NetworkX `nx.Graph` API. Ensures deterministic execution even in minimal
    environments while delegating to `networkx` when installed.
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
        seen: Set[Tuple[str, str]] = set()
        result: List[Any] = []
        for u, nbrs in self._adj.items():
            for v, d in nbrs.items():
                pair = (u, v) if u < v else (v, u)
                if pair not in seen:
                    seen.add(pair)
                    if data:
                        result.append((u, v, d))
                    else:
                        result.append((u, v))
        return result

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


# ==============================================================================
# Core Graph Algorithms & Computational Social Science Estimators
# ==============================================================================
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
    for s in nodes:
        dist: Dict[str, int] = {s: 0}
        queue: List[str] = [s]
        idx = 0
        while idx < len(queue):
            u = queue[idx]
            idx += 1
            for v in G.neighbors(u):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        tot_dist = sum(dist.values())
        reachable = len(dist) - 1
        if tot_dist > 0 and n > 1:
            cc = (reachable / float(tot_dist)) * (reachable / float(n - 1))
        else:
            cc = 0.0
        closeness[s] = cc
    return closeness


def compute_betweenness_centrality(G: Any, weight: str = "weight") -> Dict[str, float]:
    """
    Computes normalized weighted betweenness centrality using Brandes' (2001)
    shortest-path dependency accumulation algorithm. Follow NetworkX convention
    where the 'weight' attribute is interpreted as path distance cost unless
    inverted, matching standard `nx.betweenness_centrality(G, weight='weight')`.
    """
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        return nx.betweenness_centrality(G, weight=weight, normalized=True)

    nodes = G.nodes()
    n = len(nodes)
    betweenness: Dict[str, float] = {v: 0.0 for v in nodes}
    if n <= 2:
        return betweenness

    for s in nodes:
        stack: List[str] = []
        pred: Dict[str, List[str]] = {w: [] for w in nodes}
        sigma: Dict[str, float] = {w: 0.0 for w in nodes}
        sigma[s] = 1.0
        dist: Dict[str, float] = {}
        dist[s] = 0.0
        heap: List[Tuple[float, int, str, str]] = []
        counter = 0
        heapq.heappush(heap, (0.0, counter, s, s))
        seen: Dict[str, float] = {s: 0.0}

        while heap:
            d, _, pred_node, v = heapq.heappop(heap)
            if v in dist and v != s:
                continue
            sigma[v] += sigma[pred_node] if v != s else 0.0
            stack.append(v)
            dist[v] = d
            for w in G.neighbors(v):
                ew = float(G.get_edge_data(v, w).get(weight, 1.0))
                vw_dist = d + ew
                if w not in dist and (w not in seen or vw_dist < seen[w] - 1e-12):
                    seen[w] = vw_dist
                    counter += 1
                    heapq.heappush(heap, (vw_dist, counter, v, w))
                    sigma[w] = 0.0
                    pred[w] = [v]
                elif w not in dist and abs(vw_dist - seen.get(w, -1.0)) <= 1e-12:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        delta: Dict[str, float] = {w: 0.0 for w in nodes}
        while stack:
            w = stack.pop()
            coeff = (1.0 + delta[w]) / sigma[w] if sigma[w] > 0 else 0.0
            for v in pred[w]:
                delta[v] += sigma[v] * coeff
            if w != s:
                betweenness[w] += delta[w]

    scale = 1.0 / ((n - 1) * (n - 2))
    for v in betweenness:
        betweenness[v] *= scale
    return betweenness


def compute_clustering_coefficient(G: Any) -> Dict[str, float]:
    """Computes local unweighted clustering coefficient C(v) = 2*T(v) / (k_v*(k_v-1))."""
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        return nx.clustering(G)
    clustering: Dict[str, float] = {}
    for u in G.nodes():
        nbrs = G.neighbors(u)
        k = len(nbrs)
        if k < 2:
            clustering[u] = 0.0
            continue
        nbr_set = set(nbrs)
        triangles = 0
        for i in range(k):
            v = nbrs[i]
            for w in G.neighbors(v):
                if w in nbr_set and w > v:
                    triangles += 1
        clustering[u] = (2.0 * triangles) / float(k * (k - 1))
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
        raw_eff_size = nx.effective_size(G, weight=weight)
        constraint_clean = {
            k: (0.0 if (v is None or math.isnan(v)) else float(v))
            for k, v in raw_constraint.items()
        }
        eff_size_clean = {
            k: (0.0 if (v is None or math.isnan(v)) else float(v))
            for k, v in raw_eff_size.items()
        }
        return constraint_clean, eff_size_clean

    nodes = G.nodes()
    # Precompute proportional tie strengths p_ij = w_ij / sum_k w_ik
    p: Dict[str, Dict[str, float]] = {}
    m: Dict[str, Dict[str, float]] = {}
    for u in nodes:
        nbrs = G.neighbors(u)
        if not nbrs:
            p[u] = {}
            m[u] = {}
            continue
        weights = {v: float(G.get_edge_data(u, v).get(weight, 1.0)) for v in nbrs}
        tot_w = sum(weights.values())
        max_w = max(weights.values())
        p[u] = {v: (w / tot_w if tot_w > 0 else 0.0) for v, w in weights.items()}
        m[u] = {v: (w / max_w if max_w > 0 else 0.0) for v, w in weights.items()}

    constraint: Dict[str, float] = {}
    effective_size: Dict[str, float] = {}

    for i in nodes:
        nbrs_i = G.neighbors(i)
        if not nbrs_i:
            constraint[i] = 0.0
            effective_size[i] = 0.0
            continue

        # Compute Burt's Constraint C_i
        c_i = 0.0
        for j in nbrs_i:
            direct = p[i].get(j, 0.0)
            indirect = 0.0
            for q in nbrs_i:
                if q != i and q != j:
                    indirect += p[i].get(q, 0.0) * p[q].get(j, 0.0)
            c_i += (direct + indirect) ** 2
        constraint[i] = c_i

        # Compute Burt's Weighted Effective Size ES_i
        es_i = 0.0
        for j in nbrs_i:
            redundancy = 0.0
            for q in nbrs_i:
                if q != i and q != j:
                    redundancy += p[i].get(q, 0.0) * m[j].get(q, 0.0)
            es_i += 1.0 - redundancy
        effective_size[i] = es_i

    return constraint, effective_size


def detect_louvain_communities(
    G: Any, weight: str = "weight", seed: int = 42
) -> Tuple[Dict[str, int], float]:
    """
    Executes Louvain community detection (Blondel et al., 2008) to partition
    the artist network into cohesive genre/stylistic clusters and evaluates
    global Newman-Girvan Modularity Q.
    """
    if HAS_NETWORKX and isinstance(G, nx.Graph):
        communities = nx_comm.louvain_communities(G, weight=weight, seed=seed)
        modularity_q = nx_comm.modularity(G, communities, weight=weight)
        # Sort communities by size descending so Community 0 is the largest
        sorted_comms = sorted(communities, key=lambda c: (-len(c), sorted(list(c))[0]))
        node_to_comm: Dict[str, int] = {}
        for comm_id, comm_set in enumerate(sorted_comms):
            for node in comm_set:
                node_to_comm[node] = comm_id
        return node_to_comm, float(modularity_q)

    # Two-phase hierarchical Louvain modularity optimization (Blondel et al., 2008)
    rng = random.Random(seed)
    nodes = list(G.nodes())
    if not nodes:
        return {}, 0.0

    m_total = sum(float(d.get(weight, 1.0)) for _, _, d in G.edges(data=True))
    if m_total <= 0:
        return {n: 0 for n in nodes}, 0.0

    k_w: Dict[str, float] = {u: float(G.degree(u, weight=weight)) for u in nodes}
    adj: Dict[str, Dict[str, float]] = {u: {} for u in nodes}
    for u, v, d in G.edges(data=True):
        w = float(d.get(weight, 1.0))
        adj[u][v] = adj[u].get(v, 0.0) + w
        adj[v][u] = adj[v].get(u, 0.0) + w

    node_to_comm: Dict[str, int] = {u: idx for idx, u in enumerate(nodes)}

    while True:
        curr_nodes = sorted(list(set(node_to_comm.values())))
        super_adj: Dict[int, Dict[int, float]] = {c: {} for c in curr_nodes}
        super_self: Dict[int, float] = {c: 0.0 for c in curr_nodes}
        for u in nodes:
            cu = node_to_comm[u]
            for v, w in adj[u].items():
                cv = node_to_comm[v]
                if cu == cv:
                    super_self[cu] += w
                else:
                    super_adj[cu][cv] = super_adj[cu].get(cv, 0.0) + w

        super_k = {c: super_self[c] + sum(super_adj[c].values()) for c in curr_nodes}
        comm = {c: c for c in curr_nodes}
        sigma_tot = {c: super_k[c] for c in curr_nodes}

        improved = False
        local_moved = True
        passes = 0
        while local_moved and passes < 50:
            local_moved = False
            passes += 1
            order = list(curr_nodes)
            rng.shuffle(order)
            for c_node in order:
                c_old = comm[c_node]
                kc = super_k[c_node]
                sigma_tot[c_old] -= kc

                cand_w: Dict[int, float] = {}
                for nbr, w in super_adj[c_node].items():
                    cnbr = comm[nbr]
                    cand_w[cnbr] = cand_w.get(cnbr, 0.0) + w

                best_c = c_old
                k_in_old = cand_w.get(c_old, 0.0)
                base_gain = k_in_old - (sigma_tot.get(c_old, 0.0) * kc) / (2.0 * m_total)
                best_delta = 0.0

                for c_cand, k_in in cand_w.items():
                    gain = (k_in - (sigma_tot.get(c_cand, 0.0) * kc) / (2.0 * m_total)) - base_gain
                    if gain > best_delta + 1e-10:
                        best_delta = gain
                        best_c = c_cand

                comm[c_node] = best_c
                sigma_tot[best_c] = sigma_tot.get(best_c, 0.0) + kc
                if best_c != c_old:
                    local_moved = True
                    improved = True

        for u in nodes:
            node_to_comm[u] = comm[node_to_comm[u]]

        if not improved or len(set(node_to_comm.values())) == len(curr_nodes):
            break

    comm_groups: Dict[int, List[str]] = {}
    for u, cid in node_to_comm.items():
        comm_groups.setdefault(cid, []).append(u)

    sorted_groups = sorted(comm_groups.values(), key=lambda g: (-len(g), sorted(g)[0]))
    final_map: Dict[str, int] = {}
    for new_id, group in enumerate(sorted_groups):
        for u in group:
            final_map[u] = new_id

    q_val = 0.0
    for group in sorted_groups:
        group_set = set(group)
        l_c = 0.0
        d_c = 0.0
        for u in group:
            d_c += k_w[u]
            for v, w in adj[u].items():
                if v in group_set:
                    l_c += w
        l_c /= 2.0
        q_val += (l_c / m_total) - ((d_c / (2.0 * m_total)) ** 2)

    return final_map, float(q_val)


# ==============================================================================
# GEXF 1.2 Exporter for Gephi Visual Analytics
# ==============================================================================
def write_gephi_gexf(G: Any, output_path: str) -> None:
    """
    Exports the enriched graph topology to a valid GEXF 1.2 XML file.
    Configures explicit node and edge attribute schemas so Gephi automatically
    recognizes `Modularity_Class` (integer/partition) and centrality/structural
    hole metrics (float/ranking) for 1-click visual encoding.
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

    # Define Node Attributes Schema
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

    # Define Edge Attributes Schema
    attrs_edge_el = ET.SubElement(
        graph_el, "attributes", {"class": "edge", "mode": "static"}
    )
    ET.SubElement(
        attrs_edge_el,
        "attribute",
        {"id": "0", "title": "relation", "type": "string"},
    )

    # Populate Nodes
    nodes_el = ET.SubElement(graph_el, "nodes")
    for node_id, data in G.nodes(data=True):
        node_el = ET.SubElement(
            nodes_el,
            "node",
            {"id": str(node_id), "label": str(data.get("label", node_id))},
        )
        attvalues_el = ET.SubElement(node_el, "attvalues")
        for attr_id, title, _ in node_attrs_schema:
            val = data.get(title, "")
            ET.SubElement(
                attvalues_el,
                "attvalue",
                {"for": attr_id, "value": str(val)},
            )

    # Populate Edges
    edges_el = ET.SubElement(graph_el, "edges")
    for edge_idx, (u, v, edata) in enumerate(G.edges(data=True)):
        w = edata.get("weight", 1.0)
        rel = edata.get("relation", "Collaboration")
        edge_el = ET.SubElement(
            edges_el,
            "edge",
            {
                "id": str(edge_idx),
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


# ==============================================================================
# Pipeline 1: Generative Simulation Benchmark (mode='simulation')
# ==============================================================================
def build_simulation_benchmark_network(seed: int = 42) -> Any:
    """
    Constructs a parameterized 120-node synthetic music collaboration benchmark
    graph combining high intra-genre triadic closure (small-world property)
    with preferential hub attachment and 8 dedicated cross-genre bridge producers.

    Parameters:
        seed (int): Random number generator seed for exact reproducibility.

    Returns:
        Graph: Populated undirected weighted collaboration network (120 nodes).
    """
    random.seed(seed)
    G = nx.Graph() if HAS_NETWORKX else StandaloneGraph()

    communities_config = {
        "Classical & Neo-Classical": {"prefix": "CLS", "count": 28},
        "Popular Music": {"prefix": "POP", "count": 32},
        "Jazz & Fusion": {"prefix": "JAZ", "count": 26},
        "Electronic & Ambient": {"prefix": "ELC", "count": 26},
    }

    community_nodes: Dict[str, List[str]] = {}

    # 1. Instantiate genre-specific artist nodes and core hubs
    for genre, info in communities_config.items():
        nodes: List[str] = []
        for i in range(1, int(info["count"]) + 1):
            node_id = f"{info['prefix']}_Artist_{i:02d}"
            role = "Genre Hub" if i <= 2 else "Artist"
            G.add_node(node_id, label=node_id, genre=genre, role=role)
            nodes.append(node_id)
        community_nodes[genre] = nodes

    # 2. Instantiate 8 Cross-Genre Bridge Producers spanning structural holes
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

    # 3. Generate dense intra-community ties (preferential hub attachment + triadic closure)
    for genre, nodes in community_nodes.items():
        hubs = nodes[:2]
        others = nodes[2:]

        for hub in hubs:
            partners = random.sample(others, k=int(len(others) * 0.55))
            for partner in partners:
                G.add_edge(
                    hub,
                    partner,
                    weight=random.randint(2, 6),
                    relation="Intra-Genre Collab",
                )

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if not G.has_edge(nodes[i], nodes[j]) and random.random() < 0.14:
                    G.add_edge(
                        nodes[i],
                        nodes[j],
                        weight=random.randint(1, 3),
                        relation="Intra-Genre Collab",
                    )

    # 4. Generate cross-genre brokerage ties mediated by Bridge Producers
    genre_list = list(community_nodes.keys())
    for bridge in bridge_nodes:
        connected_genres = random.sample(genre_list, k=3)
        for g in connected_genres:
            targets = random.sample(community_nodes[g], k=random.randint(3, 5))
            for target in targets:
                G.add_edge(
                    bridge,
                    target,
                    weight=random.randint(2, 5),
                    relation="Cross-Genre Collab",
                )

    # 5. Introduce sparse random weak ties across genres
    all_regular_nodes = [n for nodes in community_nodes.values() for n in nodes]
    for _ in range(18):
        u, v = random.sample(all_regular_nodes, 2)
        u_genre = G.nodes[u]["genre"] if HAS_NETWORKX else G.node_attr_dict[u]["genre"]
        v_genre = G.nodes[v]["genre"] if HAS_NETWORKX else G.node_attr_dict[v]["genre"]
        if u_genre != v_genre:
            G.add_edge(u, v, weight=1, relation="Cross-Genre Collab")

    return G


# ==============================================================================
# Pipeline 2: Empirical Artist Network Loader (mode='real')
# ==============================================================================
def load_empirical_artist_network(edgelist_path: str) -> Any:
    """
    Constructs an empirical cross-genre collaboration network from a curated CSV
    edge list (`Source,Target,Weight,Relation_Type`) and enriches nodes with
    genre and role classifications.

    Parameters:
        edgelist_path (str): Path to the empirical CSV file.

    Returns:
        Graph: Populated undirected weighted empirical collaboration network.
    """
    path_obj = Path(edgelist_path)
    if not path_obj.exists():
        raise FileNotFoundError(
            f"Empirical edge list not found at '{edgelist_path}'. "
            "Verify that 'data/real_artist_edgelist.csv' exists."
        )

    G = nx.Graph() if HAS_NETWORKX else StandaloneGraph()

    with open(path_obj, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required_cols = {"Source", "Target", "Weight", "Relation_Type"}
        if reader.fieldnames is None or not required_cols.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Invalid CSV schema in {edgelist_path}. "
                f"Expected columns: {sorted(list(required_cols))}"
            )

        for row_idx, row in enumerate(reader, start=2):
            u = row["Source"].strip()
            v = row["Target"].strip()
            if not u or not v or u == v:
                continue
            try:
                weight = float(row["Weight"])
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid weight on line %d (%s -> %s); defaulting to 1.0",
                    row_idx,
                    u,
                    v,
                )
                weight = 1.0
            rel_type = row["Relation_Type"].strip() or "Cross-Genre Collab"

            for artist in (u, v):
                genre, role = EMPIRICAL_ARTIST_METADATA.get(
                    artist, ("Cross-Genre / Other", "Artist")
                )
                G.add_node(artist, label=artist, genre=genre, role=role)

            G.add_edge(
                u,
                v,
                weight=int(weight) if weight.is_integer() else weight,
                relation=rel_type,
            )

    return G


# ==============================================================================
# Unified Network Mining, Sociological Evaluation & Export Engine
# ==============================================================================
def analyze_and_export_network(
    G: Any,
    mode: str,
    gexf_path: str = "music_network_advanced.gexf",
    csv_path: str = "music_network_metrics_v2.csv",
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Executes full-spectrum network topology analysis, Louvain community detection,
    and Ronald Burt's structural holes evaluation, then exports standardized CSV
    and GEXF 1.2 deliverables.
    """
    logger.info("Initializing Complex Network & Structural Holes Analysis (mode='%s')", mode)

    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()

    # 1. Compute Classical Centralities & Clustering
    degree_cent = compute_degree_centrality(G)
    betweenness_cent = compute_betweenness_centrality(G, weight="weight")
    closeness_cent = compute_closeness_centrality(G)
    clustering_coef = compute_clustering_coefficient(G)
    avg_clustering = (
        sum(clustering_coef.values()) / float(num_nodes) if num_nodes > 0 else 0.0
    )

    # 2. Compute Louvain Community Partition & Global Modularity Q
    modularity_map, modularity_q = detect_louvain_communities(
        G, weight="weight", seed=seed
    )
    num_communities = len(set(modularity_map.values()))

    # 3. Compute Ronald Burt's Structural Holes Metrics (Constraint & Effective Size)
    constraint_map, effective_size_map = compute_burt_structural_holes(
        G, weight="weight"
    )

    # 4. Bind Enriched Sociological Attributes to Graph Nodes & Tabular Records
    records: List[Dict[str, Any]] = []
    for node_id, data in G.nodes(data=True):
        deg = int(G.degree(node_id))
        dc = round(float(degree_cent.get(node_id, 0.0)), 4)
        bc = round(float(betweenness_cent.get(node_id, 0.0)), 4)
        cc = round(float(closeness_cent.get(node_id, 0.0)), 4)
        clust = round(float(clustering_coef.get(node_id, 0.0)), 4)
        mod_class = int(modularity_map.get(node_id, 0))
        constraint_val = round(float(constraint_map.get(node_id, 0.0)), 4)
        eff_size_val = round(float(effective_size_map.get(node_id, 0.0)), 4)

        attr_target = G.nodes[node_id] if HAS_NETWORKX else G.node_attr_dict[node_id]
        attr_target["Degree"] = deg
        attr_target["Degree_Centrality"] = dc
        attr_target["Betweenness_Centrality"] = bc
        attr_target["Closeness_Centrality"] = cc
        attr_target["Clustering_Coefficient"] = clust
        attr_target["Modularity_Class"] = mod_class
        attr_target["Constraint"] = constraint_val
        attr_target["Effective_Size"] = eff_size_val

        records.append(
            {
                "Artist_ID": node_id,
                "Genre_Group": data.get("genre", "Unknown"),
                "Role": data.get("role", "Artist"),
                "Degree": deg,
                "Degree_Centrality": dc,
                "Betweenness_Centrality": bc,
                "Closeness_Centrality": cc,
                "Clustering_Coefficient": clust,
                "Modularity_Class": mod_class,
                "Constraint": constraint_val,
                "Effective_Size": eff_size_val,
            }
        )

    # Sort records deterministically by Betweenness Centrality descending
    records_sorted = sorted(
        records,
        key=lambda r: (r["Betweenness_Centrality"], r["Effective_Size"], r["Degree"]),
        reverse=True,
    )

    # 5. Export Gephi Topology File (.gexf)
    write_gephi_gexf(G, gexf_path)
    logger.info("Exported Gephi topology file with node attributes: %s", gexf_path)

    # 6. Export Node Metrics Table (.csv)
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
        df = pd.DataFrame(records)
        df.to_csv(csv_path, index=False, encoding="utf-8")
    else:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
    logger.info("Exported full sociological node metrics table: %s", csv_path)

    # 7. Structured Academic CLI Summary Report
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
        rows=sorted(records, key=lambda x: x["Degree_Centrality"], reverse=True)[:5],
    )
    _print_top_table(
        title="TOP 5 BETWEENNESS CENTRALITY NODES (Cross-Genre Shortest-Path Brokers)",
        rows=sorted(records, key=lambda x: x["Betweenness_Centrality"], reverse=True)[:5],
    )
    _print_top_table(
        title="TOP 5 STRUCTURAL HOLE SPANNERS (Lowest Burt Constraint & High Effective Size)",
        rows=sorted(
            [r for r in records if r["Degree"] >= 3],
            key=lambda x: (x["Constraint"], -x["Effective_Size"]),
        )[:5],
    )
    print("=" * 88 + "\n")

    return records_sorted


def _print_top_table(title: str, rows: List[Dict[str, Any]]) -> None:
    """Formats and prints a clean ASCII academic comparison table to stdout."""
    print(f"\n>>> {title}")
    header = (
        f"{'Artist_ID':<24} | {'Genre_Group':<25} | {'Deg':>3} | "
        f"{'Betw':>6} | {'Mod':>3} | {'Constr':>6} | {'EffSize':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{str(r['Artist_ID'])[:24]:<24} | "
            f"{str(r['Genre_Group'])[:25]:<25} | "
            f"{r['Degree']:>3d} | "
            f"{r['Betweenness_Centrality']:>6.4f} | "
            f"{r['Modularity_Class']:>3d} | "
            f"{r['Constraint']:>6.4f} | "
            f"{r['Effective_Size']:>7.4f}"
        )


# ==============================================================================
# Unified Entry Point (Supports Dual-Pipeline Switching)
# ==============================================================================
def main(
    mode: str = "real",
    edgelist_path: str = "data/real_artist_edgelist.csv",
    gexf_output: str = "music_network_advanced.gexf",
    csv_output: str = "music_network_metrics_v2.csv",
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Primary pipeline entry point supporting seamless switching between synthetic
    benchmark generation (`mode='simulation'`) and empirical streaming network
    mining (`mode='real'`).

    Parameters:
        mode (str): Execution mode ('real' or 'simulation').
        edgelist_path (str): Path to empirical edge list CSV when mode='real'.
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
        graph = load_empirical_artist_network(edgelist_path=edgelist_path)

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
            gexf_output=args.gexf,
            csv_output=args.csv,
            seed=args.seed,
        )
    except Exception as exc:
        logger.error("Pipeline execution terminated with error: %s", exc)
        sys.exit(1)