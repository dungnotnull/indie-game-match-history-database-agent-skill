# Harness Execution Flow

## Overview

This diagram shows the end-to-end execution flow of the indie-game-match-history-database harness, from user input through quality gates to final output.

## Flow Diagram

```mermaid
flowchart TD
    Start([User Input]) --> PreFlight[Pre-Flight: Language Detection]
    PreFlight -->|vi| VI[ Vietnamese Output Mode]
    PreFlight -->|en| EN[English Output Mode]
    PreFlight -->|other| EN

    VI --> Step1
    EN --> Step1

    Step1[Step 1: sub-gather-requirements]
    Step1 -->|Gate1: Object confirmed?| Gate1a{✓}
    Step1 -->|Gate1: Failed| Gate1b{✗ Ask for clarification}
    Gate1b --> Step1

    Gate1a --> Step2[Step 2: sub-evidence-collector]

    Step2 -->|Gate2: Evidence retrieved?| Gate2a{✓}
    Step2 -->|Gate2: Failed with fallback| Gate2b{⚠ Limitation flag}
    Step2 -->|Gate2: Complete failure| Error1[Error: Cannot proceed]

    Gate2a --> Step3
    Gate2b --> Step3

    Step3[Step 3: sub-core-analysis]
    Step3 -->|G1: Data model & tiering?| G1{✓}
    Step3 -->|G2: Queries & indexes?| G2{✓}
    Step3 -->|G4: Privacy addressed?| G4{✓}

    G1 --> G1fail[❌ Auto-fix or fail]
    G2 --> G2fail[❌ Auto-fix or fail]
    G4 --> G4fail[❌ Auto-fix or fail]

    G1fail -->|Retry max 2| Step3
    G2fail -->|Retry max 2| Step3
    G4fail -->|Retry max 2| Step3

    G1 --> Step4
    G2 --> Step4
    G4 --> Step4

    Step4[Step 4: sub-knowledge-updater]
    Step4 -->|Gate4: Academic source found?| Gate4a{✓}
    Step4 -->|Gate4: No sources| Gate4b{⚠ Gap flag}

    Gate4a --> Step5
    Gate4b --> Step5

    Step5[Step 5: sub-advisor]
    Step5 -->|Gate5: Valid conclusion?| Gate5a{✓}
    Step5 -->|Gate5: Invalid conclusion| Gate5b[❌ Auto-fix or fail]

    Gate5b -->|Retry max 2| Step5

    Gate5a --> QG[Step 6: Quality Gate Review]

    QG -->|U1: ≥3 sources, ≥1 academic| U1{✓}
    QG -->|U2: Disclosure before conclusion| U2{✓}
    QG -->|U3: Evidence hierarchy stated| U3{✓}
    QG -->|U4: Language matches preference| U4{✓}
    QG -->|U5: Output template complete| U5{✓}
    QG -->|U6: Claims traceable| U6{✓}

    U1 --> U1fail[❌ Auto-fix or fail]
    U2 --> U2fail[❌ Auto-fix or fail]
    U3 --> U3fail[❌ Auto-fix or fail]
    U4 --> U4fail[❌ Auto-fix or fail]
    U5 --> U5fail[❌ Auto-fix or fail]
    U6 --> U6fail[❌ Auto-fix or fail]

    U1fail -->|Retry max 2| QG
    U2fail -->|Retry max 2| QG
    U3fail -->|Retry max 2| QG
    U4fail -->|Retry max 2| QG
    U5fail -->|Retry max 2| QG
    U6fail -->|Retry max 2| QG

    U1 --> Deliver
    U2 --> Deliver
    U3 --> Deliver
    U4 --> Deliver
    U5 --> Deliver
    U6 --> Deliver

    Deliver[Deliver Output]
    Deliver --> End([User receives risk-disclosed, evidence-backed recommendation])

    Error1 --> End

    style PreFlight fill:#e1f5fe
    style Step1 fill:#f3e5f5
    style Step2 fill:#e8f5e9
    style Step3 fill:#fff3e0
    style Step4 fill:#fce4ec
    style Step5 fill:#e0f2f1
    style QG fill:#fff9c4
    style Deliver fill:#c8e6c9
    style Start fill:#b2dfdb
    style End fill:#b2dfdb
    style Error1 fill:#ffcdd2
```

## Quality Gates

### Universal Gates (U1-U6)

| Gate | Criterion | Auto-Fix |
|------|-----------|----------|
| U1 | ≥3 sources, ≥1 academic/authoritative | Search knowledge base |
| U2 | Disclosure before conclusion | Prepend disclosure section |
| U3 | Evidence hierarchy stated | Add tier labels to sources |
| U4 | Language matches preference | Translate output |
| U5 | Output template complete | Fill missing sections |
| U6 | Claims traceable | Add source references |

### Domain Gates (G1-G4)

| Gate | Criterion | Engine Module |
|------|-----------|---------------|
| G1 | Data model & tiering defined | `models.py`, `storage/tiered.py` |
| G2 | Queries & indexes designed | `storage/base.py` |
| G3 | Scalability addressed | `storage/sqlite.py` |
| G4 | Privacy/retention addressed | `privacy.py` |

## Error Recovery

| Error Type | Action | Retry Limit |
|------------|--------|-------------|
| No object of analysis | Ask for clarification | 3 |
| Evidence fetch failed | Fallback to knowledge base | 2 |
| Quality gate failed | Auto-fix or manual | 2 |
| Language mismatch | Translate | 1 |

## Graceful Degradation

The harness operates at 5 degradation levels:

| Level | Capability | Limitation Flag |
|-------|------------|-----------------|
| 0 | Full operation | None |
| 1 | Real-time data unavailable | Using cached sources |
| 2 | Knowledge base unavailable | Expert judgment only |
| 3 | Sub-skill unavailable | Manual analysis |
| 4 | Harness failed | Cannot complete |

## Parallel Execution

When `enable_parallel_subskills = true`:

```
Step 1 → Step 2 (parallel starts) → Step 3 (parallel starts) → Step 4 (parallel starts) → Step 5
              ↓                        ↓                         ↓
         Evidence              Core Analysis           Knowledge Update
```

Max concurrent subskills: 3 (configurable via `max_concurrent_subskills`).

## Engine Grounding

Each step grounds its analysis in the tested engine:

- **Step 3**: References `indie_match_history/models.py` for data model
- **Step 3**: References `indie_match_history/storage/` for tiering
- **Step 3**: References `indie_match_history/privacy.py` for GDPR/COPPA
- **Step 3**: References `indie_match_history/ratings.py` for rating systems

This ensures recommendations are not theoretical but validated by code.
