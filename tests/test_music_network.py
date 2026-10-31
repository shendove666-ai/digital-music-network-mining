from __future__ import annotations

import csv
import math
import unittest
from pathlib import Path

import networkx as nx

from music_network_mining import (
    compute_betweenness_centrality,
    load_empirical_artist_network,
)
from null_model_analysis import randomised_copy, run_null_model


ROOT = Path(__file__).resolve().parents[1]
EDGE_FILE = ROOT / "data" / "real_artist_edgelist.csv"


class ArtistDataTests(unittest.TestCase):
    def test_curated_edge_file_integrity(self) -> None:
        with EDGE_FILE.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 260)
        pairs = set()
        for row in rows:
            self.assertTrue(row["Source"].strip())
            self.assertTrue(row["Target"].strip())
            self.assertNotEqual(row["Source"], row["Target"])
            self.assertGreater(float(row["Weight"]), 0.0)
            pair = tuple(sorted((row["Source"], row["Target"])))
            self.assertNotIn(pair, pairs)
            pairs.add(pair)

    def test_saved_network_size(self) -> None:
        graph = load_empirical_artist_network(str(EDGE_FILE))
        self.assertEqual(graph.number_of_nodes(), 120)
        self.assertEqual(graph.number_of_edges(), 260)

    def test_weight_is_converted_to_distance_for_betweenness(self) -> None:
        graph = nx.Graph()
        graph.add_edge("a", "b", weight=10)
        graph.add_edge("b", "c", weight=10)
        graph.add_edge("a", "c", weight=1)
        result = compute_betweenness_centrality(graph)
        self.assertGreater(result["b"], 0.0)

    def test_null_graph_preserves_degree_edge_count_and_weights(self) -> None:
        graph = load_empirical_artist_network(str(EDGE_FILE))
        randomised = randomised_copy(graph, seed=99, swaps_per_edge=2)
        self.assertEqual(graph.number_of_edges(), randomised.number_of_edges())
        self.assertEqual(
            sorted(dict(graph.degree()).values()),
            sorted(dict(randomised.degree()).values()),
        )
        original_weights = sorted(data["weight"] for _, _, data in graph.edges(data=True))
        null_weights = sorted(data["weight"] for _, _, data in randomised.edges(data=True))
        self.assertEqual(original_weights, null_weights)

    def test_small_null_run_returns_finite_results(self) -> None:
        graph = load_empirical_artist_network(str(EDGE_FILE))
        runs, summary = run_null_model(graph, repetitions=3, seed=7, swaps_per_edge=1)
        self.assertEqual(len(runs), 3)
        self.assertEqual(len(summary), 2)
        for row in summary:
            self.assertTrue(math.isfinite(row["observed"]))
            self.assertTrue(math.isfinite(row["null_mean"]))


if __name__ == "__main__":
    unittest.main()
