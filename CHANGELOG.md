# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-09-24

### Added
- `Paper` data model with validation.
- Dataset reading and writing with provenance metadata.
- Citation graph construction, year and citation-count filters.
- PageRank influence ranking with deterministic tie breaking.
- Network summary statistics.
- Graph JSON and ranking CSV export.
- Data provider interface with JSON-file and OpenAlex adapters.
- Command line interface: `summary`, `rank`, `export`, `fetch`.
- CI workflow (lint, types, test matrix, build) and release workflow.
