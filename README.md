# Source-backed Music Collaboration Network Analysis

An exploratory Python/NetworkX study of a small, verifiable artist-collaboration sample. It asks how recording-level co-credits form local clusters and potential brokerage positions. It does **not** claim to map the global music industry or any artist's complete discography.

The analysis was rebuilt from MusicBrainz rather than relying on the original hand-curated edge list. Every displayed edge can be traced to recording-level evidence in this repository.

## Portfolio snapshot

This project demonstrates how to define a music collaboration edge from traceable recording credits, then test whether the resulting network structure differs from a degree-preserving reference. In the selected 40-artist sample, 410 recording-level evidence rows support 48 artist-pair edges. Observed clustering exceeds the 500-network null distribution (0.2055 versus 0.0585 on average; empirical two-sided p = 0.0060). These are sample-specific findings, with source and coverage limits documented below.

## What the current dataset contains

| Item | Current value |
| --- | ---: |
| Manually confirmed artist identities | 40 |
| Artists with at least one verified co-credit | 35 |
| Artists with no retrieved co-credit | 5 |
| Distinct recording-level evidence rows | 410 |
| Aggregated artist-pair edges | 48 |
| Retrieval timestamp | 2026-10-31 (UTC) |

The 40-person roster comes from the most connected names in the original exploratory file. This only defines a practical retrieval scope; no legacy relationship or weight is reused as evidence.

## Definition of a collaboration

Two artists receive one collaboration observation only when both appear in the artist-credit of the same [MusicBrainz recording](https://musicbrainz.org/doc/MusicBrainz_API). The weight of an artist pair is the number of **distinct recording MBIDs** where both artists are credited.

- MBIDs distinguish artists with the same or similar names.
- Recording MBIDs are deduplicated, so reissues do not raise an edge's weight.
- Sharing a compilation or a release alone is not counted as a collaboration.
- No relationship is inferred from genre, reputation, memory, or co-appearance outside a shared recording credit.
- The raw MusicBrainz data used here are available under [CC0](https://musicbrainz.org/doc/About/Data_License); this repository's code is available under the MIT License.

## Results for this sample

The verified graph has 40 nodes and 48 weighted edges (density 0.0615). Five roster artists have no verified shared recording credit and remain in the graph as isolates rather than being silently removed.

The highest betweenness scores in this sample are Thundercat (0.4804), 坂本龍一 / Ryuichi Sakamoto (0.4008), Hildur Guðnadóttir (0.3414), David Bowie (0.3239), and Robert Glasper (0.2915). These are properties of this 40-artist, MusicBrainz-indexed sample—not claims about universal influence or artistic importance.

To give the topology a fair reference point, the repository generates 500 degree-preserving random networks: every randomized graph keeps the observed number of nodes, edges, and each node's degree, while reassigning the observed edge weights. The observed average clustering is higher than that null distribution (0.2055 vs. 0.0585 ± 0.0348; empirical two-sided p = 0.0060). Weighted modularity is higher numerically (0.7706 vs. 0.6875 ± 0.0559), but this comparison is not statistically decisive at the 0.05 level (p = 0.0978). It is therefore reported as an exploratory difference, not as evidence of a confirmed community effect.

## Measurement and reproducibility

The analysis reports these complementary quantities:

| Quantity | Operational definition |
| --- | --- |
| Degree and degree centrality | Number of distinct collaborators, divided by the full roster size minus one for normalized degree. |
| Closeness | Unweighted shortest paths with the Wasserman–Faust correction for the fraction of the roster reached. |
| Betweenness | Normalized share of shortest paths passing through a node, with distance equal to the reciprocal of recording co-credit count. |
| Clustering | Mean unweighted local clustering over the full roster, including the five isolates. |
| Modularity | Weighted Newman–Girvan modularity of the Louvain partition at resolution 1 and seed 42 for the reported graph. |
| Structural holes | Weighted ego-network constraint and effective size. Undefined isolate values are exported as zero. |

Genre and role are curated attributes. The degree and betweenness tables rank
nodes on graph metrics, and the structural-hole table includes nodes of degree
at least three. Community IDs are ordered by group size and then the smallest
node ID within each tied group.

The 410 observation rows represent 404 distinct recording MBIDs. Three
recordings each contribute three artist pairs. Repeated references to the same
recording MBID for one pair count once. The degree-preserving null model shuffles
the observed edge weights after each graph's swap batch. It preserves per-node
degree and the multiset of edge weights. Components, node strengths, and
triangles projected from recordings can change. The empirical two-sided
statistic counts null values at least as far from the null sample mean as the
observed value, with a plus-one adjustment.

The archived NetworkX 3.7 results were replayed with Python 3.13.17, NumPy 2.5.4,
and SciPy 1.18.1. Use the dependency versions and backend when comparing
exports. In this environment, NetworkX's weighted all-node effective-size path
and its explicit node-wise path differ for 13 artists at the exported precision.
The node-wise path agrees with the standalone weighted calculation to rounding
error. Treat archived effective-size values as backend-specific pending
reconciliation. The clustering and modularity null-model rows replay exactly.

The standalone weighted betweenness branch treats path distances within
one trillionth as tied. Use the same branch for comparisons on nearly equal
path costs. Small or dense graphs can fail to admit the requested number of
null-model swaps.

## Repository map

```text
data/
├── musicbrainz/
│   ├── artist_registry.csv              # 40 manually confirmed identities and MBIDs
│   ├── artist_candidates.csv            # candidate search results retained for audit
│   ├── recording_evidence.csv           # 410 recording-level source records
│   └── verified_artist_edgelist.csv     # 48 weighted artist-pair edges
├── real_artist_edgelist.csv             # legacy, uncited exploratory file; not used for results above
musicbrainz_provenance.py                # reproducible search/review/collection workflow
music_network_mining.py                  # centrality, communities, structural holes, Gephi export
null_model_analysis.py                   # degree-preserving random-network comparison
output/
├── musicbrainz_verified_metrics.csv
├── musicbrainz_verified_network.gexf
└── musicbrainz_null_model/
    ├── runs.csv
    └── summary.csv
```

## Reproduce the verified analysis

Run the commands from the repository root. The default real-mode input is the
legacy exploratory edge list. Pass the verified edge list and registry
explicitly to reproduce the results above. Use separate output locations for
different datasets or collection runs, and create parent directories for
custom export paths before running. Evidence and edge tables are written in
sequence, so check both outputs before treating them as one complete batch.

```powershell
pip install -r requirements.txt

# Analyze the verified co-credit network and export a Gephi file.
python music_network_mining.py --mode real `
  --input data/musicbrainz/verified_artist_edgelist.csv `
  --artist-registry data/musicbrainz/artist_registry.csv `
  --gexf output/musicbrainz_verified_network.gexf `
  --csv output/musicbrainz_verified_metrics.csv

# Compare with 500 degree-preserving random graphs.
python null_model_analysis.py `
  --input data/musicbrainz/verified_artist_edgelist.csv `
  --artist-registry data/musicbrainz/artist_registry.csv `
  --repetitions 500 `
  --output-dir output/musicbrainz_null_model

# Run validation tests.
python -m unittest discover -s tests -v
```

`musicbrainz_verified_network.gexf` can be opened directly in Gephi. Map node size to degree or betweenness, color nodes by `Modularity_Class`, and retain the data and methodological limits above in any visualization caption.

## Rebuild or audit the evidence

The evidence workflow deliberately separates name matching from data collection. A search rank is never treated as proof of identity.

```powershell
# Generate a short list from the legacy file only.
python musicbrainz_provenance.py prepare --top 40

# Retrieve possible identities for manual review.
python musicbrainz_provenance.py search --limit 15

# After reviewing every row in artist_registry.csv as confirmed or excluded:
python musicbrainz_provenance.py collect
```

For each evidence row, `recording_evidence.csv` stores both artists' MBIDs, the recording MBID and URL, the chosen release MBID and URL, release date, and retrieval time. See the Chinese step-by-step guide in [docs/MUSICBRAINZ_GUIDE_CN.md](docs/MUSICBRAINZ_GUIDE_CN.md).

## Scope and limitations

- MusicBrainz coverage and artist credits are community-maintained and may be incomplete or corrected later.
- The roster is intentionally small and selection is not random; it should not support population-level claims about music genres or the industry.
- Co-credit is a narrow operational definition of collaboration. It does not capture producing, sampling, live performance, mentorship, or informal creative influence unless these appear in a shared recording credit.
- Centrality is a structural measure inside this graph. It is not a ranking of artistic value, fame, or commercial success.

## References

- Blondel, V. D., Guillaume, J.-L., Lambiotte, R., & Lefebvre, E. (2008). Fast unfolding of communities in large networks.
- Burt, R. S. (1992). *Structural Holes: The Social Structure of Competition*.
- MusicBrainz. [Web Service API](https://musicbrainz.org/doc/MusicBrainz_API) and [data licence](https://musicbrainz.org/doc/About/Data_License).
