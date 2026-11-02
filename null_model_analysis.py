#!/usr/bin/env python3
"""Degree-preserving null-model analysis for an empirical artist network.

The original synthetic graph in ``music_network_mining.py`` is useful for
checking whether the metrics recover deliberately planted bridge nodes. It is
not a statistical null model because its density and construction differ from
the empirical graph. This module provides the appropriate comparison: repeated
degree-preserving edge swaps on the observed topology, with the observed edge
weights randomly reassigned after every swap.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path
from statistics import fmean, stdev
from typing import Dict, Iterable, List

import networkx as nx
from networkx.algorithms import community as nx_comm

from music_network_mining import load_empirical_artist_network


def graph_statistics(graph: nx.Graph, seed: int) -> Dict[str, float]:
    """Return the two graph-level statistics used in the comparison."""
    communities = nx_comm.louvain_communities(graph, weight="weight", seed=seed)
    return {
        "average_clustering": float(nx.average_clustering(graph)),
        "weighted_modularity": float(
            nx_comm.modularity(graph, communities, weight="weight")
        ),
    }


def randomised_copy(graph: nx.Graph, seed: int, swaps_per_edge: int = 10) -> nx.Graph:
    """Randomise topology while preserving degree and edge count.

    ``double_edge_swap`` preserves every node's degree.  Reassigning the
    observed weights preserves the empirical weight distribution without
    preserving which artist pair received which weight.
    """
    rng = random.Random(seed)
    randomised = nx.Graph()
    randomised.add_nodes_from(graph.nodes(data=True))
    randomised.add_edges_from(graph.edges())

    edge_count = randomised.number_of_edges()
    if edge_count >= 2:
        target_swaps = max(edge_count, edge_count * swaps_per_edge)
        nx.double_edge_swap(
            randomised,
            nswap=target_swaps,
            max_tries=target_swaps * 20,
            seed=seed,
        )

    weights = [float(data.get("weight", 1.0)) for _, _, data in graph.edges(data=True)]
    rng.shuffle(weights)
    for (left, right), weight in zip(randomised.edges(), weights):
        randomised[left][right]["weight"] = weight
    return randomised


def empirical_two_sided_p(observed: float, values: Iterable[float]) -> float:
    """Return a finite-sample two-sided empirical p-value around the null mean."""
    samples = list(values)
    centre = fmean(samples)
    observed_distance = abs(observed - centre)
    at_least_as_extreme = sum(abs(value - centre) >= observed_distance for value in samples)
    return (at_least_as_extreme + 1.0) / (len(samples) + 1.0)


def summarise(observed: float, values: List[float]) -> Dict[str, float]:
    null_mean = fmean(values)
    null_sd = stdev(values) if len(values) > 1 else 0.0
    z_score = (observed - null_mean) / null_sd if null_sd > 0 else math.nan
    return {
        "observed": observed,
        "null_mean": null_mean,
        "null_sd": null_sd,
        "z_score": z_score,
        "empirical_p_two_sided": empirical_two_sided_p(observed, values),
    }


def run_null_model(
    graph: nx.Graph,
    repetitions: int = 500,
    seed: int = 42,
    swaps_per_edge: int = 10,
) -> tuple[List[Dict[str, float]], List[Dict[str, float]]]:
    if repetitions < 2:
        raise ValueError("repetitions must be at least 2")

    observed = graph_statistics(graph, seed=seed)
    runs: List[Dict[str, float]] = []
    for run_index in range(repetitions):
        run_seed = seed + run_index + 1
        null_graph = randomised_copy(graph, run_seed, swaps_per_edge=swaps_per_edge)
        stats = graph_statistics(null_graph, seed=run_seed)
        runs.append({"run": run_index + 1, "seed": run_seed, **stats})

    summary: List[Dict[str, float]] = []
    for metric, observed_value in observed.items():
        metric_values = [row[metric] for row in runs]
        summary.append(
            {
                "metric": metric,
                "repetitions": repetitions,
                **summarise(observed_value, metric_values),
            }
        )
    return runs, summary


def write_csv(path: Path, rows: List[Dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/real_artist_edgelist.csv")
    parser.add_argument(
        "--artist-registry",
        default=None,
        help="Optional confirmed MusicBrainz registry to retain the full sampled roster.",
    )
    parser.add_argument("--repetitions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--swaps-per-edge", type=int, default=10)
    parser.add_argument("--output-dir", default="output/null_model")
    args = parser.parse_args()

    graph = load_empirical_artist_network(args.input, args.artist_registry)
    runs, summary = run_null_model(
        graph,
        repetitions=args.repetitions,
        seed=args.seed,
        swaps_per_edge=args.swaps_per_edge,
    )
    output_dir = Path(args.output_dir)
    write_csv(output_dir / "runs.csv", runs)
    write_csv(output_dir / "summary.csv", summary)

    for row in summary:
        print(
            f"{row['metric']}: observed={row['observed']:.4f}, "
            f"null={row['null_mean']:.4f} +/- {row['null_sd']:.4f}, "
            f"z={row['z_score']:.2f}, p={row['empirical_p_two_sided']:.4f}"
        )


if __name__ == "__main__":
    main()
