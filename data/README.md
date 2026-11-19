# Data provenance

## Dataset used by the current analysis

`musicbrainz/` is the source-backed dataset used by the README's reported results.

- `artist_registry.csv` records the 40 identity decisions. `confirmed` means a human reviewed the MusicBrainz candidate; `excluded` means an ambiguous candidate was deliberately not used.
- `artist_candidates.csv` retains the ranked search candidates so that the identity decisions can be audited.
- `recording_evidence.csv` has one row for each distinct artist-pair/recording-MBID observation. It includes artist and recording MBIDs, source URLs, release metadata, and a retrieval timestamp.
- `verified_artist_edgelist.csv` aggregates the evidence. Its `Weight` is the number of distinct shared recording MBIDs for that artist pair.

The data are retrieved from MusicBrainz. Its core data are released under [CC0](https://musicbrainz.org/doc/About/Data_License). The cache directory is intentionally excluded from version control because it is reproducible API-response material.

## Legacy exploratory file

`real_artist_edgelist.csv` is retained solely as the project's original exploratory input. It contains 120 artists and 260 hand-curated links without row-level evidence and is **not** the basis for the current results, figures, CV claims, or personal-statement claims. It is used only to construct the manageable 40-name shortlist for the source-backed rebuild.

Do not add citations or weights to that legacy file by guesswork. If the verified sample is extended, repeat the documented MusicBrainz identity-review and recording-evidence workflow instead.

## Evidence metadata and legacy outputs

The evidence timestamp records the start of the collection run. Cached API
responses can be older than that timestamp. The release field describes the
earliest candidate among the lookup results, with missing dates ordered last
and MBID used as a tie-breaker. A recording can still support a co-credit when
its release ID or date is unavailable.

| Archive entry | Dataset |
| --- | --- |
| `output/musicbrainz_verified_metrics.csv`, `output/musicbrainz_verified_network.gexf`, `output/musicbrainz_null_model/` | The verified 40-artist, 48-edge analysis and its null model. |
| `output/music_network_metrics_v2.csv`, `output/music_network_advanced.gexf`, `output/null_model/` | The legacy 120-artist, 260-edge exploratory analysis and its null model. |
| `output/music_network_metrics_simulation_v2.csv`, `output/music_network_simulation_advanced.gexf` | The seeded 120-node, 425-edge simulation. |
| `docs/figures/` | Archived visual assets. The repository has no generation record linking these images to the 40-artist analysis. |
