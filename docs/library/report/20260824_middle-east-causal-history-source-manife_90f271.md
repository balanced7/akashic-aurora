---
akashic_id: art_20260824_middle-east-causal-history-source-manife_90f271
akashic_sha: 3db3637289e8
schema_version: 1
status: draft
type: report
date: 2026-08-24
title: middle-east-causal-history-source-manifest
gist: "Source coverage, independence cautions, known holes, falsifiers, and publication gates for the Middle East causal history."
visibility: fleet
body_type: markdown
seats: [codex]
category: [testing, narrative]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-24T20:51:27"
updated: "2026-08-24T20:51:27"
---
<!-- GENERATED PROJECTION of art_20260824_middle-east-causal-history-source-manife_90f271 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# middle-east-causal-history-source-manifest

# Source manifest: Middle East causal history

Status: **in flight** | Started: 2026-08-24 | Companion narrative: [middle-east-causal-history-2026-08-24.md](middle-east-causal-history-2026-08-24.md)

This manifest exists so narrative coherence cannot masquerade as research coverage.

## Current coverage

### Video testimony

| Source | Coverage | How read | Limits |
|---|---|---|---|
| [Jordan Peterson, “The Brutal Reality of the Middle East - Mosab Hassan Yousef, EP 443”](https://www.youtube.com/watch?v=I5VPFw0vI6U) | Complete public YouTube program, approximately 02:01:38 | Canonical `agent_cli.py captions` verb produced TXT and VTT; four independent end-to-end readings; SHA-256 `A66C68CF8C96753B3F26223013C0E424C2C5C7FCA1460D32FC5C01ADFE3E461F` | Auto-captions contain transcription errors. The public video ends before an advertised Daily Wire Plus continuation. Peterson and Yousef are interlocutors, not independent confirmation when one proposes and the other assents. |

Local evidence:

- `X:\captions\The_Brutal_Reality_of_the_Middle_East_Mosab_Hassan_Yousef_EP_443-[I5VPFw0vI6U].en.txt` - 2,681 lines, 17,884 words.
- `X:\captions\The_Brutal_Reality_of_the_Middle_East_Mosab_Hassan_Yousef_EP_443-[I5VPFw0vI6U].en.vtt` - timestamped original-caption surface.
- Advertisements occupy TXT lines 620-649, 1153-1187, and 1657-1686.

Fan geometry:

| Pass | Coverage | Lens | Result |
|---|---|---|---|
| Conducting read | 2,681 / 2,681 lines | Whole-argument and philosophical reading | Complete |
| `yousef_causal_read` | 2,681 / 2,681 lines | Causal reconstruction, firsthand versus inference | Complete |
| `yousef_adversarial_read` | 2,681 / 2,681 lines | Epistemic audit, overreach, corroboration tests | Complete |
| `yousef_system_map` | 2,681 / 2,681 lines | Hamas/Iran/Israel/civilians/protests/virtues mapping | Complete |

The fan increases error detection; it does not turn four readings of one source into four sources.

### Protest activity

| Source | Version and coverage used | Method | Limits |
|---|---|---|---|
| [Crowd Counting Consortium, Phase 2, 2021-2024](https://doi.org/10.7910/DVN/9MMYDI) | Dataverse v2.1, released 2025-10-16; 128 MB TSV | Streamed 2023-10 through 2024-12; ASCII-stable claim classifier | Phase boundary and changing collection practices make December-January comparisons less secure than within-Phase-3 comparisons. Event count is not attendance. |
| [Crowd Counting Consortium, Phase 3, 2025-present](https://doi.org/10.7910/DVN/RI9JFU) | Dataverse v17.0, released 2026-07-08; 55,061 rows dated 2025-01-01 through 2026-03-31 | Lossless byte mapping for mixed legacy encodings; core pro-Palestine classifier over titles, claims, and organizations; daily, weekly, and monthly counts | U.S. only. Keyword classification can misclassify mixed or counter-demonstrations. Crowd-size estimates are too sparse for a confident attendance series. March 2026 is the latest event date in this release, not the current date. |

Core-classifier receipts around the January 20, 2025 foreign-aid order:

| Window | Events | Per day |
|---|---:|---:|
| 2025-01-02 through 2025-01-19 | 475 | 26.39 |
| 2025-01-20 through 2025-02-06 | 488 | 27.11 |
| Week 2025-01-13 through 2025-01-19 | 206 | 29.43 |
| Week 2025-01-20 through 2025-01-26 | 259 | 37.00 |
| February 2025 | 592 | 21.14 |
| March 2025 | 865 | 27.90 |

The simple U.S. event-count hypothesis predicts an immediate negative discontinuity at the cutoff. The observed series does not show one. This result does **not** test non-U.S. demonstrations or attendance where size is unreported.

### USAID, fiscal sponsors, and foreign influence

| Claim surface | What it establishes | What it does not establish |
|---|---|---|
| [January 20, 2025 executive order](https://www.whitehouse.gov/presidential-actions/2025/01/reevaluating-and-realigning-united-states-foreign-aid/) | A 90-day pause on new obligations and disbursements of foreign development assistance pending review | Which specific payment actually stopped on which date |
| [USAspending award AIDOAAG1400006](https://www.usaspending.gov/award/ASST_NON_AIDOAAG1400006_7200) | USAID obligated $699,966 to Tides Center for a 2014-2016 overseas-assistance grant | Any connection to post-October-7 demonstrations |
| [USAID Civil Society Innovation Initiative description](https://2017-2020.usaid.gov/sites/default/files/documents/1866/DRG-Users-Guide-3.15.2019.pdf) | Tides Center was fiscal agent for award AID-OAA-A-16-00007 supporting regional civil-society innovation hubs in developing countries | Domestic protest spending or Palestine Legal funding from the award |
| [Tides statement on its USAID partnership](https://www.tides.org/statement/tides-partnership-with-usaid/) | Tides says $24.5 million supported global civil society through July 2024, another $1.5 million supported transparency work through 2019, and $680,807 in health subawards ended January 2025 | Independent proof that no fungibility or cross-subsidy occurred. This is the recipient's own account and needs award/subaward records. |
| [Congressional hearing record on nonprofit networks](https://www.congress.gov/119/chrg/CHRG-119hhrg61125/CHRG-119hhrg61125.pdf) | Critics explicitly allege an adjacency from USAID to Tides to domestic groups | The same hearing contains the admission that there is no concrete proof that the federal dollars received were the dollars passed to the named domestic groups |
| [ODNI statement, July 9, 2024](https://www.dni.gov/index.php/newsroom/press-releases/press-releases-2024/3842-statement-from-director-of-national-intelligence-avril-haines-on-recent-iranian-influence-efforts) | U.S. intelligence observed Iranian government-linked actors posing as activists, encouraging Gaza protests, and even providing financial support to protesters | Scale, recipient identities, or proof that ordinary protesters knowingly worked for Iran |
| [Science study, “Aiding peace or conflict? The impact of USAID cuts on violence”](https://doi.org/10.1126/science.aed6802) | A quasi-experimental study reports increased conflict, including protests and riots, in more aid-exposed African regions after the shutdown | U.S. pro-Palestine mobilization; all regions; benignity of every USAID program |

Provisional judgment: there are documented private funding networks and documented Iranian influence attempts. The direct USAID-to-domestic-protest path and the claimed January 2025 protest discontinuity are not currently established.

### October 7 and armed-group conduct

| Source | Use | Independence cautions |
|---|---|---|
| [Human Rights Watch, “I Can't Erase All the Blood from My Mind”](https://www.hrw.org/report/2024/07/17/i-cant-erase-all-blood-my-mind/palestinian-armed-groups-october-7-assault-israel) | Event-level reconstruction of planned attacks, murder, hostage-taking, multiple armed groups, and some civilian participation | Rights organization with its own framework; methods and incident evidence must be inspected, not brand-ratified |
| [AP investigation of Hamas training sites and rehearsals](https://apnews.com/article/israel-palestinian-war-hamas-attack-border-wall-aa0b0f5f3613b6c6882cf37168e8e8ed) | Verified training-site imagery, mock settlement/base, barrier breaching, hostage drills, and external assistance claims | Some assistance attribution derives from Hamas statements or intelligence assessments |
| [AP visit to the large Erez-area tunnel](https://apnews.com/article/israel-tunnel-war-gaza-hamas-350dbabc2890ee3c4fc2ec33c2a53f09) | Physical scale, vehicle capacity, proximity to Erez, and the offensive function alleged after October 7 | Access was organized by the Israeli military; claims beyond what AP observed require separate support |
| [IDF Be'eri inquiry](https://www.idf.il/en/mini-sites/710-the-inquiries/all-of-the-710-inquiries/battle-of-kibbutz-beeri-the-inquiry/) | Israeli military account of severe preparation, warning, command, and response failures | The institution is investigating itself; affected families and independent evidence may contest findings |
| [AP on possible friendly fire at Be'eri](https://apnews.com/article/3b6fdd4592957340b32a8ee71505b8e9) | Families' demand to investigate whether Israeli fire killed hostages during the response | Does not erase Hamas's hostage-taking or establish how every victim died |

### Lebanon and Hezbollah's social order

| Source | Use | Limits |
|---|---|---|
| [Cammett and Issar, “Bricks and Mortar Clientelism”](https://pmc.ncbi.nlm.nih.gov/articles/PMC4029429/) | Empirical mapping of sectarian welfare provision; Hezbollah priority for fighters and martyr families alongside some broader service provision | Older fieldwork; allocation and institutions may have changed |
| [Cammett, “Partisan Activism and Access to Welfare in Lebanon”](https://pmc.ncbi.nlm.nih.gov/articles/PMC4043299/) | The Martyrs' Institution provides health, schooling, material, and other benefits to eligible fighter families | Structural, not a complete individual recruitment biography |
| [AP, “Lebanon's Shiite Muslims pay high price...”](https://www.ap.org/news-highlights/spotlights/2024/lebanons-shiite-muslims-pay-high-price-in-war-between-israel-and-hezbollah/) | Named civilian suffering, perceptions of collective punishment, Israeli military claims, and Lebanese criticism of Hezbollah's choices in one account | A reported cross-section, not a population survey |
| [Al Jazeera profile of Mohammad Ali Janbin's family](https://www.aljazeera.com/features/2013/6/10/family-of-hezbollah-fighter-refuse-to-mourn) | Family meaning, martyrdom, protection, and intergenerational identity | Sympathetic family testimony; does not establish recruitment economics by itself |

Terminology rule: the Palestinian Authority prisoner/martyr payment system and Hezbollah's Martyrs' Institution, salaries, and welfare network must be traced separately. “Pay to slay” is a political label, not a license to merge institutions.

### Mosab Hassan Yousef corroboration and correction set

| Claim | Corroboration or correction |
|---|---|
| Long service as a Shin Bet source; handler relationship | [Contemporaneous Guardian report and later asylum coverage](https://www.theguardian.com/world/2010/jun/30/hamas-israel-spy); former handler Gonen Ben Itzhak publicly supported him |
| First Intifada entirely engineered from abroad | Requires correction: his witnessed coercive mechanisms can be true while scholarship describing a locally emergent uprising disputes the origin theory |
| Palestinian identity is non-existent | Category error: absence of prior sovereignty does not establish absence of a nation or identity; late-Ottoman scholarship already examines developing Jewish and Palestinian political identities |
| Every Muslim identity is dangerous | Polemical generalization contradicted by the diversity he himself acknowledges; not an empirical result |
| Most October 7 rape and kidnapping was committed by Gazan civilians | Some civilian participation is independently documented; “most” is not established by the transcript or current event-level investigations |
| Israel never acts without evidence and current civilian harm is unavoidable | His selected operational experience is relevant but cannot certify every unit, detention, strike, policy, or accountability mechanism |
| Arafat had exactly $9 billion and his wife killed him | Corruption and diversion merit documentation; the exact figure is unsettled and [French prosecutors found insufficient evidence of third-party intervention in Arafat's death](https://time.com/4021200/yasser-arafat-not-poisoned/) |
| USAID funded the protest movement | The transcript never mentions USAID and supplies no award, organizer, transfer, or time-series evidence |

## Source independence protocol

No institution receives independence by brand.

For each source, record:

1. the specific unit and author;
2. mandate and legal or political authority;
3. access to the event;
4. local staff and intermediary dependence;
5. underlying evidence and whether it is published;
6. detection, omission, and reporting incentives;
7. corrections and adverse-interest admissions;
8. whether another cited source is actually downstream of it.

Political UN resolutions, OCHA relays, UNRWA operational records, UN investigative commissions, Israeli military inquiries, Israeli ministries, Hamas statements, Hezbollah media, Iranian doctrine, NGO reports, journalism, survivor testimony, and forensic work are different source classes. None may be collapsed into “the UN says,” “Israel says,” or “reports say.”

## Known holes

1. No full historical primary-document corpus has yet been frozen.
2. Gaza and Palestinian human-witness selection is not yet adequate.
3. No incident sample of Israeli strikes has yet been fully reconstructed from target claim through post-strike investigation.
4. The current protest test is U.S. event counts, not worldwide participation or crowd size.
5. USAID subaward and restricted-fund tracing is incomplete.
6. The Iranian network is supported at the capability and sponsorship levels, but this manifest does not yet carry a complete money/command timeline for each partner.
7. The public YouTube transcript excludes the paid continuation.
8. Several October 7 atrocity accounts circulated early and were later corrected; the final witness set must distinguish verified horrors from contaminated stories rather than using either to erase the other.
9. Current events after the latest cited source must be refreshed before publication.

## Initial falsifiers

| Provisional claim | Evidence that would change it |
|---|---|
| No immediate U.S. pro-Palestine event-count collapse at the USAID cutoff | A reproducible classifier or corrected CCC records showing the observed post-cutoff counts are artifacts; a better nationwide event dataset showing a sharp discontinuity |
| USAID-to-Tides adjacency does not yet prove protest funding | Restricted-award records, subaward ledgers, bank records, or recipient admissions tracing USAID dollars into a domestic organizer's mobilization expenses |
| Iran was a strategic sponsor and capability-builder, not publicly proven tactical commander of October 7 | Authenticated pre-attack orders, planning attendance, command intercepts, or planner testimony establishing operational approval or direction |
| Yousef is strongest near firsthand experience and weakest at population-wide inference | Independent records falsifying his named operational history, or broad population evidence validating the universal claims he makes |
| Hezbollah's welfare system is both service and mobilization infrastructure | Field evidence showing services and recruitment/support are institutionally unrelated, or current evidence that the described priority systems no longer operate |

## Publication gate

Before this work may be called a verified report:

- reconcile the final chapter list, source denominator, source classes, date boundary, fan/shard list, and human-witness roster in this manifest;
- attach a claim ledger with a citation and confidence state for every load-bearing factual sentence;
- conduct an Israeli-claims adversary pass, a Palestinian-claims adversary pass, a Lebanese sovereignty pass, an Iranian-network pass, and a legal-classification pass;
- verify quotations against audio or original-language text;
- separate historical fact, legal judgment, moral judgment, and causal inference in the prose;
- render and inspect the final visual/report artifact before adoption.
