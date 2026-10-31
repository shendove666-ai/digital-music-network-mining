#!/usr/bin/env python3
"""Build a source-backed artist collaboration network from MusicBrainz.

Workflow: prepare legacy names, search identity candidates, manually confirm
the identities, then collect recording-level co-credit evidence.  The highest
search result is never treated as automatic identity confirmation.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


API_ROOT = "https://musicbrainz.org/ws/2"
PROJECT_URL = "https://github.com/shendove666-ai/digital-music-network-mining"
USER_AGENT = f"WenMaoMusicNetwork/1.0 ({PROJECT_URL})"
MBID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
REGISTRY_FIELDS = [
    "legacy_name", "legacy_degree", "artist_mbid", "canonical_name",
    "disambiguation", "confirmation_status", "review_note",
]
CANDIDATE_FIELDS = [
    "legacy_name", "legacy_degree", "candidate_rank", "score", "artist_mbid",
    "name", "sort_name", "type", "country", "disambiguation", "musicbrainz_url",
]
EVIDENCE_FIELDS = [
    "artist_a", "artist_a_mbid", "artist_b", "artist_b_mbid",
    "recording_title", "recording_mbid", "release_title", "release_mbid",
    "release_date", "recording_url", "release_url", "retrieved_at_utc",
]


class MusicBrainzClient:
    """Rate-limited JSON client with retry and optional disk cache."""

    def __init__(self, cache_dir: Path | None = None, delay: float = 1.1) -> None:
        self.cache_dir = cache_dir
        self.delay = delay
        self.last_request = 0.0

    def get(
        self, resource: str, params: Dict[str, Any], cache_key: str | None = None
    ) -> Dict[str, Any]:
        cache_path = None
        if cache_key and self.cache_dir:
            cache_path = self.cache_dir / f"{cache_key}.json"
            if cache_path.exists():
                return json.loads(cache_path.read_text(encoding="utf-8"))

        query = urllib.parse.urlencode({**params, "fmt": "json"})
        url = f"{API_ROOT}/{resource}?{query}"
        error: Exception | None = None
        for attempt in range(4):
            remaining = self.delay - (time.monotonic() - self.last_request)
            if remaining > 0:
                time.sleep(remaining)
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    payload = json.load(response)
                self.last_request = time.monotonic()
                if cache_path:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                return payload
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                error = exc
                self.last_request = time.monotonic()
                if attempt < 3:
                    time.sleep(2**attempt)
        raise RuntimeError(f"MusicBrainz request failed: {url}\n{error}")


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepare_registry(input_path: Path, output_path: Path, top: int, force: bool) -> None:
    if output_path.exists() and not force:
        raise FileExistsError(
            f"{output_path} already exists; use --force only if replacement is intended"
        )
    legacy = read_csv(input_path)
    degree: Counter[str] = Counter()
    for row in legacy:
        degree[row["Source"].strip()] += 1
        degree[row["Target"].strip()] += 1
    ranked = sorted(degree.items(), key=lambda item: (-item[1], item[0].casefold()))
    rows = [
        {
            "legacy_name": name,
            "legacy_degree": value,
            "artist_mbid": "",
            "canonical_name": "",
            "disambiguation": "",
            "confirmation_status": "",
            "review_note": "",
        }
        for name, value in ranked[:top]
    ]
    write_csv(output_path, REGISTRY_FIELDS, rows)
    print(f"Wrote {len(rows)} artist names to {output_path}")


def search_candidates(registry_path: Path, output_path: Path, limit: int) -> None:
    registry = read_csv(registry_path)
    client = MusicBrainzClient()
    candidates: List[Dict[str, Any]] = []
    for index, artist in enumerate(registry, start=1):
        name = artist["legacy_name"]
        print(f"[{index}/{len(registry)}] Searching {name}", flush=True)
        payload = client.get("artist/", {"query": f'artist:"{name}"', "limit": limit})
        for rank, candidate in enumerate(payload.get("artists", []), start=1):
            mbid = candidate.get("id", "")
            candidates.append(
                {
                    "legacy_name": name,
                    "legacy_degree": artist["legacy_degree"],
                    "candidate_rank": rank,
                    "score": candidate.get("score", ""),
                    "artist_mbid": mbid,
                    "name": candidate.get("name", ""),
                    "sort_name": candidate.get("sort-name", ""),
                    "type": candidate.get("type", ""),
                    "country": candidate.get("country", ""),
                    "disambiguation": candidate.get("disambiguation", ""),
                    "musicbrainz_url": f"https://musicbrainz.org/artist/{mbid}" if mbid else "",
                }
            )
    write_csv(output_path, CANDIDATE_FIELDS, candidates)
    print(f"Wrote {len(candidates)} candidates to {output_path}")
    print("Review candidates manually; rank 1 is not automatic confirmation.")


def load_confirmed_registry(path: Path) -> List[Dict[str, str]]:
    rows = read_csv(path)
    unresolved = [
        row["legacy_name"]
        for row in rows
        if row["confirmation_status"].strip().casefold() not in {"confirmed", "excluded"}
    ]
    if unresolved:
        preview = ", ".join(unresolved[:8])
        raise ValueError(
            f"Every registry row must be confirmed or excluded. Unresolved: {preview}"
            + (" ..." if len(unresolved) > 8 else "")
        )
    confirmed = [
        row for row in rows if row["confirmation_status"].strip().casefold() == "confirmed"
    ]
    for row in confirmed:
        if not MBID_RE.fullmatch(row["artist_mbid"].strip()):
            raise ValueError(f"Invalid artist MBID for {row['legacy_name']}: {row['artist_mbid']}")
        if not row["canonical_name"].strip():
            raise ValueError(f"Missing canonical_name for {row['legacy_name']}")
    ids = [row["artist_mbid"].casefold() for row in confirmed]
    if len(ids) != len(set(ids)):
        raise ValueError("Two confirmed rows use the same artist MBID")
    return confirmed


def earliest_release(releases: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    if not releases:
        return {"id": "", "title": "", "date": ""}
    chosen = sorted(
        releases, key=lambda item: (item.get("date") or "9999", item.get("id", ""))
    )[0]
    return {
        "id": chosen.get("id", ""),
        "title": chosen.get("title", ""),
        "date": chosen.get("date", ""),
    }


def credited_artist_ids(recording: Dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for credit in recording.get("artist-credit", []):
        if isinstance(credit, dict):
            artist = credit.get("artist", {})
            if artist.get("id"):
                ids.add(artist["id"])
    return ids


def collect_evidence(
    registry_path: Path,
    evidence_path: Path,
    edges_path: Path,
    cache_dir: Path,
    max_pages: int | None,
) -> None:
    confirmed = load_confirmed_registry(registry_path)
    by_mbid = {row["artist_mbid"]: row for row in confirmed}
    selected_ids = set(by_mbid)
    client = MusicBrainzClient(cache_dir=cache_dir)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    evidence: Dict[tuple[str, str, str], Dict[str, Any]] = {}

    for artist_index, artist in enumerate(confirmed, start=1):
        artist_mbid = artist["artist_mbid"]
        offset = 0
        page = 0
        while True:
            print(
                f"[{artist_index}/{len(confirmed)}] {artist['canonical_name']} "
                f"recordings offset={offset}",
                flush=True,
            )
            payload = client.get(
                "recording",
                {
                    "artist": artist_mbid,
                    # MusicBrainz browse requests accept artist credits here,
                    # but release expansion requires a separate recording lookup.
                    "inc": "artist-credits",
                    "limit": 100,
                    "offset": offset,
                },
                cache_key=f"recordings_{artist_mbid}_{offset}",
            )
            recordings = payload.get("recordings", [])
            for recording in recordings:
                recording_mbid = recording.get("id", "")
                coartists = sorted(credited_artist_ids(recording).intersection(selected_ids))
                if len(coartists) < 2 or artist_mbid not in coartists:
                    continue
                recording_detail = client.get(
                    f"recording/{recording_mbid}",
                    {"inc": "artist-credits+releases"},
                    cache_key=f"recording_detail_{recording_mbid}",
                )
                release = earliest_release(recording_detail.get("releases", []))
                for left_index, left in enumerate(coartists):
                    for right in coartists[left_index + 1 :]:
                        evidence[(left, right, recording_mbid)] = {
                            "artist_a": by_mbid[left]["canonical_name"],
                            "artist_a_mbid": left,
                            "artist_b": by_mbid[right]["canonical_name"],
                            "artist_b_mbid": right,
                            "recording_title": recording.get("title", ""),
                            "recording_mbid": recording_mbid,
                            "release_title": release["title"],
                            "release_mbid": release["id"],
                            "release_date": release["date"],
                            "recording_url": f"https://musicbrainz.org/recording/{recording_mbid}",
                            "release_url": (
                                f"https://musicbrainz.org/release/{release['id']}"
                                if release["id"] else ""
                            ),
                            "retrieved_at_utc": retrieved_at,
                        }
            offset += len(recordings)
            page += 1
            total = int(payload.get("recording-count", offset))
            if not recordings or offset >= total or (max_pages and page >= max_pages):
                break

    evidence_rows = [evidence[key] for key in sorted(evidence)]
    write_csv(evidence_path, EVIDENCE_FIELDS, evidence_rows)
    pair_recordings: Dict[tuple[str, str, str, str], set[str]] = {}
    for row in evidence_rows:
        pair = (
            row["artist_a"], row["artist_a_mbid"],
            row["artist_b"], row["artist_b_mbid"],
        )
        pair_recordings.setdefault(pair, set()).add(row["recording_mbid"])
    edge_rows = [
        {
            "Source": pair[0],
            "Target": pair[2],
            "Weight": len(recordings),
            "Relation_Type": "MusicBrainz recording co-credit",
            "Source_MBID": pair[1],
            "Target_MBID": pair[3],
            "Weight_Definition": "count of distinct co-credited MusicBrainz recording MBIDs",
        }
        for pair, recordings in sorted(pair_recordings.items())
    ]
    edge_fields = [
        "Source", "Target", "Weight", "Relation_Type", "Source_MBID",
        "Target_MBID", "Weight_Definition",
    ]
    write_csv(edges_path, edge_fields, edge_rows)
    print(f"Wrote {len(evidence_rows)} evidence rows to {evidence_path}")
    print(f"Wrote {len(edge_rows)} verified edges to {edges_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Create a registry from legacy names")
    prepare.add_argument("--input", default="data/real_artist_edgelist.csv")
    prepare.add_argument("--output", default="data/musicbrainz/artist_registry.csv")
    prepare.add_argument("--top", type=int, default=40)
    prepare.add_argument("--force", action="store_true")
    search = commands.add_parser("search", help="Search MusicBrainz identity candidates")
    search.add_argument("--registry", default="data/musicbrainz/artist_registry.csv")
    search.add_argument("--output", default="data/musicbrainz/artist_candidates.csv")
    search.add_argument("--limit", type=int, default=5)
    collect = commands.add_parser("collect", help="Collect evidence and aggregate edges")
    collect.add_argument("--registry", default="data/musicbrainz/artist_registry.csv")
    collect.add_argument("--evidence", default="data/musicbrainz/recording_evidence.csv")
    collect.add_argument("--edges", default="data/musicbrainz/verified_artist_edgelist.csv")
    collect.add_argument("--cache-dir", default="data/musicbrainz/cache")
    collect.add_argument("--max-pages", type=int, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        if args.top < 2:
            raise ValueError("--top must be at least 2")
        prepare_registry(Path(args.input), Path(args.output), args.top, args.force)
    elif args.command == "search":
        search_candidates(Path(args.registry), Path(args.output), args.limit)
    elif args.command == "collect":
        collect_evidence(
            Path(args.registry), Path(args.evidence), Path(args.edges),
            Path(args.cache_dir), args.max_pages,
        )


if __name__ == "__main__":
    main()
