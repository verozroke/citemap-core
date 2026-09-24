# citemap-core

[![CI](https://github.com/YOUR-USERNAME/citemap-core/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR-USERNAME/citemap-core/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Citation network analysis for **CiteMap**, an interactive explorer of academic
citation networks. This package is the analysis core behind the CiteMap web
interface: it turns a list of papers and their references into a directed
citation graph, ranks papers by structural influence, and exports the result
in a format the frontend can draw directly.

It can also be used on its own, from the command line or from Python, for
small bibliometric studies such as finding the foundational papers of a
research area before writing a literature review.

## Features

- **Graph building.** Papers become nodes, citations become edges from the
  citing to the cited paper. References that point outside the dataset and
  self-citations are ignored.
- **Influence ranking.** Papers are ranked by PageRank, which rewards being
  cited by other influential papers rather than by raw citation counts.
  Ordering is deterministic, so the same input always gives the same ranking.
- **Filtering** by publication year and by global citation count.
- **Summary statistics:** size, density, connected components, isolated
  papers, year range.
- **Export** to graph JSON (`nodes` / `links`, ready for D3.js or
  Cytoscape.js) and ranking CSV.
- **Data providers:** an offline JSON dataset adapter and an adapter for the
  open [OpenAlex](https://openalex.org) API, behind one common interface.

## Installation

Requires Python 3.10 or newer.

```bash
git clone https://github.com/YOUR-USERNAME/citemap-core.git
cd citemap-core
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .                   # add ".[dev]" for the test and lint tools
```

## Quick start

A small synthetic network ships with the repository in
[`data/sample_network.json`](data/sample_network.json).

```console
$ citemap summary data/sample_network.json
papers            14
citations         26
density           0.1429
components        1
isolated papers   0
years             1998..2023

$ citemap rank data/sample_network.json --top 5
  #  pagerank  local  year  title
  1    0.2603      4  1998  A Statistical Model of Citation Networks
  2    0.1178      3  2006  Topic Discovery in Research Corpora
  3    0.1075      3  2003  Link Analysis for Scholarly Retrieval
  4    0.0817      3  2009  Co-citation Clustering at Scale
  5    0.0597      2  2013  Embedding Scientific Abstracts
```

Papers ranked 2 and 3 are both cited three times inside the network, yet
PageRank separates them: the 2006 paper is cited by works that are themselves
cited more. This is the difference between counting citations and measuring
influence.

More commands:

```bash
# only papers from 2010 onward with at least 100 citations, saved to CSV
citemap rank data/sample_network.json --from-year 2010 --min-citations 100 --csv ranking.csv

# graph JSON for the CiteMap frontend
citemap export data/sample_network.json --out graph.json

# download the neighbourhood of a real paper from OpenAlex
citemap fetch W2741809807 --out network.json --mailto you@example.org
```

## Using it from Python

```python
from citemap import build_citation_graph, load_dataset, network_summary, rank_papers
from citemap.export import write_graph_json

graph = build_citation_graph(load_dataset("data/sample_network.json"))
print(network_summary(graph))

for paper in rank_papers(graph, top=3):
    print(f"{paper.pagerank:.3f}  {paper.title}")

write_graph_json(graph, "graph.json")
```

## Dataset format

```json
{
  "meta": {"source": "OpenAlex", "seed": "W2741809807"},
  "papers": [
    {
      "id": "W2741809807",
      "title": "The state of OA",
      "year": 2018,
      "authors": ["Heather Piwowar", "Jason Priem"],
      "cited_by_count": 1257,
      "references": ["W1560783210", "W1724212071"]
    }
  ]
}
```

Only `id` and `title` are required. The `meta` block is optional and is kept
for provenance, so every dataset records where it came from.

## OpenAlex access

`citemap fetch` works without credentials but with a small daily budget.
For regular use, create a free key at <https://openalex.org/settings/api> and
set it as an environment variable; it is never stored in the repository.

```bash
export OPENALEX_API_KEY=your-key       # Windows PowerShell: $env:OPENALEX_API_KEY="your-key"
```

## Reproducibility

- Tests and continuous integration never call the network: the OpenAlex
  adapter receives its HTTP function by injection and tests supply a fake.
- The sample dataset is versioned with the code, and `fetch` writes the data
  source and seed into every dataset it creates.
- Rankings are deterministic, including tie breaking.
- A test compares PageRank with a result solved by hand, not only with the
  library's own output.

## Project layout

```
src/citemap/
  models.py      Paper data model and validation
  dataset.py     reading and writing dataset files
  graph.py       graph construction and filters
  metrics.py     PageRank ranking and summary statistics
  export.py      graph JSON and ranking CSV
  providers.py   data source port with JSON-file and OpenAlex adapters
  cli.py         command line interface
tests/           pytest suite, one file per module
data/            sample dataset
.github/         CI/CD workflows, issue and pull request templates
```

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .   # style and lint
mypy                                    # strict static typing
pytest --cov                            # tests, fails below 90 % coverage
pytest -m network                       # optional live test against OpenAlex
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch and commit conventions.

## Continuous integration and delivery

| Workflow | Trigger | What it does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | push to `main`, pull request | lint, format check, strict mypy; tests on Python 3.10 to 3.13 (Linux) and 3.12 (Windows, macOS) with a coverage gate; builds and smoke tests the wheel |
| [`release.yml`](.github/workflows/release.yml) | tag `v*.*.*` | checks tag against package version, re-runs tests, builds, publishes a GitHub Release with the wheel and sdist |

Dependabot opens weekly pull requests for outdated Python packages and
GitHub Actions, and each of those pull requests goes through the CI pipeline.

## Citing

If you use this software in academic work, please cite it using the metadata
in [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button
for it.

## License

[MIT](LICENSE). The sample dataset is synthetic and released under CC0.
