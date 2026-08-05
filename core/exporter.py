"""
core.exporter
=============

Turns a :class:`~core.models.PlaylistResult` into files on disk:

* ``.m3u``  — VirtualDJ-compatible extended M3U playlist
* ``.csv``  — flat spreadsheet of every track + metadata
* ``.json`` — full structured dump (tracks + generation metadata)
* a plain-text playlist report summarizing BPM/energy progression,
  genre balance, and any warnings raised during generation.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from .models import PlaylistResult
from .utils import format_duration, safe_filename

logger = logging.getLogger("omniplaylist.exporter")


def export_m3u(result: PlaylistResult, output_path: str | Path) -> Path:
    """Write an Extended M3U file VirtualDJ can import directly.

    Uses the ``#EXTM3U`` / ``#EXTINF`` format:
    ``#EXTINF:<seconds>,<Artist> - <Title>`` followed by the absolute file path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["#EXTM3U"]
    for entry in result.tracks:
        duration = int(entry.length_seconds) if entry.length_seconds else -1
        label = entry.display_name
        lines.append(f"#EXTINF:{duration},{label}")
        lines.append(entry.filepath)

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Wrote M3U playlist: %s (%d tracks)", output_path, len(result.tracks))
    return output_path


def export_csv(result: PlaylistResult, output_path: str | Path) -> Path:
    """Write a flat CSV, one row per track, with every metadata column."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not result.tracks:
        output_path.write_text("", encoding="utf-8")
        return output_path

    fieldnames = list(result.tracks[0].to_dict().keys())
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for track in result.tracks:
            writer.writerow(track.to_dict())

    logger.info("Wrote CSV export: %s", output_path)
    return output_path


def export_json(result: PlaylistResult, output_path: str | Path) -> Path:
    """Write a structured JSON dump: generation metadata + full track list."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "preset": result.preset_name,
        "track_count": result.track_count,
        "total_duration_seconds": result.total_duration_seconds,
        "total_duration_formatted": format_duration(result.total_duration_seconds),
        "warnings": result.warnings,
        "tracks": [t.to_dict() for t in result.tracks],
    }
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote JSON export: %s", output_path)
    return output_path


def build_report_text(result: PlaylistResult) -> str:
    """Render a human-readable plaintext playlist report."""
    lines = []
    lines.append("=" * 60)
    lines.append("OMNIPLAYLIST — PLAYLIST REPORT")
    lines.append("=" * 60)
    lines.append(f"Preset:           {result.preset_name}")
    lines.append(f"Track count:      {result.track_count}")
    lines.append(f"Total duration:   {format_duration(result.total_duration_seconds)}")
    lines.append(f"Generated at:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if result.warnings:
        lines.append("WARNINGS:")
        for w in result.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    lines.append("-" * 60)
    lines.append(f"{'#':<4}{'Time':<9}{'BPM':<7}{'Key':<6}{'Energy':<8}Artist - Title")
    lines.append("-" * 60)
    for t in result.tracks:
        pos = t.playlist_position or 0
        time_str = format_duration(t.running_time_seconds)
        bpm_str = f"{t.bpm:.0f}" if t.has_bpm else "--"
        key_str = t.camelot_key or "--"
        energy_str = f"{t.energy_score:.0f}"
        lines.append(
            f"{pos:<4}{time_str:<9}{bpm_str:<7}{key_str:<6}{energy_str:<8}{t.display_name}"
        )

    lines.append("-" * 60)

    # Genre balance summary
    counts: dict[str, int] = {}
    for t in result.tracks:
        for g in t.detected_genres or [t.genre or "Unclassified"]:
            counts[g] = counts.get(g, 0) + 1
    if counts:
        lines.append("")
        lines.append("Genre balance:")
        total = sum(counts.values())
        for g, c in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
            pct = (c / total) * 100 if total else 0
            lines.append(f"  {g:<20} {c:>4}  ({pct:5.1f}%)")

    return "\n".join(lines)


def export_report(result: PlaylistResult, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_report_text(result), encoding="utf-8")
    logger.info("Wrote playlist report: %s", output_path)
    return output_path


def export_all(
    result: PlaylistResult, output_dir: str | Path, base_name: str
) -> dict[str, Path]:
    """Convenience helper: write .m3u, .csv, .json, and a .txt report in one call."""
    output_dir = Path(output_dir)
    base_name = safe_filename(base_name)

    paths = {
        "m3u": export_m3u(result, output_dir / f"{base_name}.m3u"),
        "csv": export_csv(result, output_dir / f"{base_name}.csv"),
        "json": export_json(result, output_dir / f"{base_name}.json"),
        "report": export_report(result, output_dir / f"{base_name}_report.txt"),
    }
    return paths
