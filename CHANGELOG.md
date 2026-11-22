# Changelog

## [0.1.4](https://github.com/andrelair-platform/ktayl-data-platform/compare/ktayl-data-platform-v0.1.3...ktayl-data-platform-v0.1.4) (2026-11-22)


### Features

* **catalog:** generated data catalog + PII register; ADR-013/014 (catalog, MDM) ([#42](https://github.com/andrelair-platform/ktayl-data-platform/issues/42)) ([efcdde5](https://github.com/andrelair-platform/ktayl-data-platform/commit/efcdde543aae08516a90aa8a4fb29932153d03b9))
* **dataops:** close silent-failure gap (ADR-015) — not-empty test + alert ([#47](https://github.com/andrelair-platform/ktayl-data-platform/issues/47)) ([fad8426](https://github.com/andrelair-platform/ktayl-data-platform/commit/fad84262a9429c4a4806adad2791abdc57d71cd9))

## [0.1.3](https://github.com/andrelair-platform/ktayl-data-platform/compare/ktayl-data-platform-v0.1.2...ktayl-data-platform-v0.1.3) (2026-11-20)


### Features

* **DP-101:** Slice 2 — underwriting as 2nd source → authoritative GWP (closes DP-007) ([#18](https://github.com/andrelair-platform/ktayl-data-platform/issues/18)) ([22ea630](https://github.com/andrelair-platform/ktayl-data-platform/commit/22ea630e286e9f65e98a0b43bcae6122a6a93b0c))
* **governance:** data-quality + PII gates on the served mart ([#22](https://github.com/andrelair-platform/ktayl-data-platform/issues/22)) ([1269d71](https://github.com/andrelair-platform/ktayl-data-platform/commit/1269d71f4c2d51178574a8780c0de69d41f98b8a))
* **lake:** S3 raw-lake runtime — keyless producer + DuckDB OLAP transform (ADR-008) ([#27](https://github.com/andrelair-platform/ktayl-data-platform/issues/27)) ([9e8b5ed](https://github.com/andrelair-platform/ktayl-data-platform/commit/9e8b5ed20a7265a62aa2e182c2c8516aa55bc721))
* **mdm:** Slice-2 conformed dimensions (dim_policy/customer/lob) — ADR-007 keystone ([#26](https://github.com/andrelair-platform/ktayl-data-platform/issues/26)) ([712184c](https://github.com/andrelair-platform/ktayl-data-platform/commit/712184c27016f0e607f0773c84344617831176f4))
* **orchestration:** Dagster + dlt + dbt + ML asset graph (ADR-010 proof) ([#32](https://github.com/andrelair-platform/ktayl-data-platform/issues/32)) ([ecfeed8](https://github.com/andrelair-platform/ktayl-data-platform/commit/ecfeed81a248c47aee55fbd1b06389c4ba7491db))
* **semantic:** Cube model — policy_portfolio governed metrics over the gold mart (ADR-009 proof) ([#30](https://github.com/andrelair-platform/ktayl-data-platform/issues/30)) ([ff17b14](https://github.com/andrelair-platform/ktayl-data-platform/commit/ff17b1404fdb4a46abdcd1b51d11271653061463))

## [0.1.2](https://github.com/andrelair-platform/ktayl-data-platform/compare/ktayl-data-platform-v0.1.1...ktayl-data-platform-v0.1.2) (2026-09-27)


### Features

* **DP-007:** resolve GWP annualisation via a guarded interim contract ([05c9d8f](https://github.com/andrelair-platform/ktayl-data-platform/commit/05c9d8f09b417ce6f319145141bf60c41045d878))

## [0.1.1](https://github.com/andrelair-platform/ktayl-data-platform/compare/ktayl-data-platform-v0.1.0...ktayl-data-platform-v0.1.1) (2026-09-27)


### Features

* ktayl-data-platform code (dbt + ingest + Metabase provisioner) ([2e8fdc4](https://github.com/andrelair-platform/ktayl-data-platform/commit/2e8fdc42161183eba3b8ec00a15cf765b40368ef))

## Changelog

All notable changes to ktayl-data-platform are documented here.

This file is maintained by [release-please](https://github.com/googleapis/release-please).
