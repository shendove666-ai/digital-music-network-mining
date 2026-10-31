# Data provenance and schema

`real_artist_edgelist.csv` is a hand-curated exploratory sample. It is not a
complete discography and, in its current version, the rows do not yet contain
source citations. Results derived from it must therefore be described as
properties of this curated sample, not as claims about the global music
industry.

## Current columns

- `Source`, `Target`: recording artists or producers;
- `Weight`: a positive collaboration-strength value;
- `Relation_Type`: an intra-genre or cross-genre label derived from the
  project's four broad genre groups.

## Required provenance upgrade

Before this dataset is used for research claims, every row should add:

- `Evidence_URL`: a stable MusicBrainz, Discogs, AllMusic, label, or official
  release page that names both collaborators;
- `Evidence_Title`: the release, track, or project supporting the tie;
- `Evidence_Date`: release year or publication date;
- `Retrieved_At`: date on which the source was checked;
- `Weight_Definition`: the mechanical rule used to derive the weight.

If a reproducible weight cannot be derived, the defensible alternative is to
analyse the network as unweighted. Empty evidence fields must never be filled
with guessed or generated citations.
