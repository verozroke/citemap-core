"""Command line interface: ``citemap summary | rank | export | fetch``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import networkx as nx

from citemap import __version__
from citemap.dataset import DatasetError, load_dataset, save_dataset
from citemap.export import write_graph_json, write_ranking_csv
from citemap.graph import build_citation_graph, filter_by_min_citations, filter_by_year
from citemap.metrics import network_summary, rank_papers
from citemap.providers import OpenAlexProvider, ProviderError


def _add_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("dataset", type=Path, help="path to a citemap dataset JSON file")
    parser.add_argument("--from-year", type=int, default=None, help="keep papers from this year")
    parser.add_argument("--to-year", type=int, default=None, help="keep papers up to this year")
    parser.add_argument(
        "--min-citations",
        type=int,
        default=0,
        help="keep papers with at least this many global citations",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="citemap",
        description="Analyse citation networks: summary statistics, influence ranking, export.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    summary = sub.add_parser("summary", help="print descriptive statistics of the network")
    _add_filter_arguments(summary)

    rank = sub.add_parser("rank", help="rank papers by PageRank influence")
    _add_filter_arguments(rank)
    rank.add_argument("--top", type=int, default=10, help="number of papers to show")
    rank.add_argument("--csv", type=Path, default=None, help="also write the ranking to CSV")

    export = sub.add_parser("export", help="write graph JSON for the CiteMap frontend")
    _add_filter_arguments(export)
    export.add_argument("--out", type=Path, required=True, help="output JSON file")

    fetch = sub.add_parser("fetch", help="download a citation neighbourhood from OpenAlex")
    fetch.add_argument("seed", help="OpenAlex work id, e.g. W2741809807")
    fetch.add_argument("--out", type=Path, required=True, help="output dataset JSON file")
    fetch.add_argument("--mailto", default=None, help="contact e-mail for polite API use")
    fetch.add_argument("--max-citing", type=int, default=50, help="citing works to include")
    return parser


def _load_filtered(args: argparse.Namespace) -> nx.DiGraph[str]:
    graph = build_citation_graph(load_dataset(args.dataset))
    graph = filter_by_year(graph, args.from_year, args.to_year)
    if args.min_citations:
        graph = filter_by_min_citations(graph, args.min_citations)
    return graph


def _cmd_summary(args: argparse.Namespace) -> None:
    s = network_summary(_load_filtered(args))
    years = f"{s.year_min}..{s.year_max}" if s.year_min is not None else "n/a"
    print(f"papers            {s.papers}")
    print(f"citations         {s.citations}")
    print(f"density           {s.density:.4f}")
    print(f"components        {s.components}")
    print(f"isolated papers   {s.isolated_papers}")
    print(f"years             {years}")


def _cmd_rank(args: argparse.Namespace) -> None:
    ranking = rank_papers(_load_filtered(args), top=args.top)
    print(f"{'#':>3}  {'pagerank':>8}  {'local':>5}  {'year':>4}  title")
    for position, item in enumerate(ranking, start=1):
        year = item.year if item.year is not None else "----"
        line = f"{position:>3}  {item.pagerank:8.4f}  {item.local_citations:>5}  {year:>4}"
        print(f"{line}  {item.title}")
    if args.csv:
        write_ranking_csv(ranking, args.csv)
        print(f"ranking written to {args.csv}")


def _cmd_export(args: argparse.Namespace) -> None:
    graph = _load_filtered(args)
    write_graph_json(graph, args.out)
    print(f"{graph.number_of_nodes()} papers, {graph.number_of_edges()} links -> {args.out}")


def _cmd_fetch(args: argparse.Namespace) -> None:
    provider = OpenAlexProvider(mailto=args.mailto, max_citing=args.max_citing)
    papers = provider.fetch_network(args.seed)
    save_dataset(papers, args.out, meta={"source": "OpenAlex", "seed": args.seed})
    print(f"{len(papers)} papers saved to {args.out}")


COMMANDS = {
    "summary": _cmd_summary,
    "rank": _cmd_rank,
    "export": _cmd_export,
    "fetch": _cmd_fetch,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        COMMANDS[args.command](args)
    except (DatasetError, ProviderError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
