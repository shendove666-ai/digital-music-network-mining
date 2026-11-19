from __future__ import annotations

import csv
import math
import unittest
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import networkx as nx

from music_network_mining import (
    StandaloneGraph,
    _top_five,
    compute_betweenness_centrality,
    compute_burt_structural_holes,
    compute_closeness_centrality,
    compute_clustering_coefficient,
    load_empirical_artist_network,
)
from null_model_analysis import randomised_copy, run_null_model
from musicbrainz_provenance import earliest_release, prepare_registry, read_csv


ROOT = Path(__file__).resolve().parents[1]
EDGE_FILE = ROOT / "data" / "real_artist_edgelist.csv"
VERIFIED_EDGE_FILE = ROOT / "data" / "musicbrainz" / "verified_artist_edgelist.csv"
VERIFIED_REGISTRY = ROOT / "data" / "musicbrainz" / "artist_registry.csv"
VERIFIED_EVIDENCE = ROOT / "data" / "musicbrainz" / "recording_evidence.csv"


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

    def test_verified_musicbrainz_roster_keeps_isolates_and_alias_metadata(self) -> None:
        graph = load_empirical_artist_network(
            str(VERIFIED_EDGE_FILE), str(VERIFIED_REGISTRY)
        )
        self.assertEqual(graph.number_of_nodes(), 40)
        self.assertEqual(graph.number_of_edges(), 48)
        self.assertEqual(graph.degree("Max Richter"), 0)
        self.assertEqual(graph.nodes["坂本龍一"]["genre"], "Classical & Neo-Classical")

    def test_recording_observations_rebuild_verified_edge_weights(self) -> None:
        evidence = read_csv(VERIFIED_EVIDENCE)
        observations = {
            (row["artist_a_mbid"], row["artist_b_mbid"], row["recording_mbid"])
            for row in evidence
        }
        self.assertEqual(len(evidence), 410)
        self.assertEqual(len(observations), len(evidence))
        self.assertEqual(len({recording for _, _, recording in observations}), 404)
        weights_from_evidence = Counter((a, b) for a, b, _ in observations)
        saved_weights = {
            (row["Source_MBID"], row["Target_MBID"]): int(row["Weight"])
            for row in read_csv(VERIFIED_EDGE_FILE)
        }
        self.assertEqual(weights_from_evidence, saved_weights)

    def test_standalone_order_and_path_metrics(self) -> None:
        graph = StandaloneGraph()
        reference = nx.Graph()
        for artist in ("z", "a", "b", "isolated"):
            graph.add_node(artist)
            reference.add_node(artist)
        for source, target, weight in (("a", "b", 2), ("z", "a", 4), ("z", "b", 1)):
            graph.add_edge(source, target, weight=weight)
            reference.add_edge(source, target, weight=weight)
        self.assertEqual(graph.edges(), [("z", "a"), ("z", "b"), ("a", "b")])
        for metric in (
            compute_betweenness_centrality,
            compute_closeness_centrality,
            compute_clustering_coefficient,
        ):
            standalone_values = metric(graph)
            reference_values = metric(reference)
            self.assertEqual(list(standalone_values), list(reference_values))
            for artist, value in reference_values.items():
                self.assertAlmostEqual(standalone_values[artist], value)

    def test_weighted_effective_size_matches_nodewise_formula(self) -> None:
        standalone = StandaloneGraph()
        reference = nx.Graph()
        for left, right, weight in (("a", "b", 2), ("a", "c", 3), ("b", "c", 5)):
            standalone.add_edge(left, right, weight=weight)
            reference.add_edge(left, right, weight=weight)
        _, effective_sizes = compute_burt_structural_holes(standalone)
        nodewise = nx.effective_size(reference, nodes=list(reference), weight="weight")
        for artist, expected in {"a": 1.0, "b": 39 / 35, "c": 43 / 30}.items():
            self.assertAlmostEqual(effective_sizes[artist], expected)
            self.assertAlmostEqual(nodewise[artist], expected)

    def test_release_choice_uses_date_and_mbid_with_stable_ties(self) -> None:
        releases = [
            {"id": "c", "date": "", "title": "Undated"},
            {"id": "z", "date": "2000", "title": "Later ID"},
            {"id": "a", "date": "2000", "title": "First matching row"},
            {"id": "a", "date": "2000", "title": "Later matching row"},
        ]
        self.assertEqual(earliest_release(releases), releases[2])
        self.assertEqual(earliest_release([]), {"id": "", "title": "", "date": ""})

    def test_top_five_preserves_stable_ties_and_nonfinite_order(self) -> None:
        rows = [{"artist": str(index), "score": index % 3} for index in range(12)]

        def score(row):
            return row["score"]

        for sample in (rows, rows[:2], rows + [{"artist": "nonfinite", "score": math.nan}]):
            for descending in (False, True):
                self.assertEqual(
                    _top_five(sample, key=score, descending=descending),
                    sorted(sample, key=score, reverse=descending)[:5],
                )

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
            dict(graph.degree()),
            dict(randomised.degree()),
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

    def test_prepare_registry_selects_unique_high_degree_artists(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "registry.csv"
            prepare_registry(EDGE_FILE, output, top=40, force=False)
            rows = read_csv(output)
        self.assertEqual(len(rows), 40)
        self.assertEqual(len({row["legacy_name"] for row in rows}), 40)
        degrees = [int(row["legacy_degree"]) for row in rows]
        self.assertEqual(degrees, sorted(degrees, reverse=True))
        self.assertTrue(all(not row["artist_mbid"] for row in rows))


if __name__ == "__main__":
    unittest.main()
