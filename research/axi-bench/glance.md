# AXI bench: `glance`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 34/35 (97%) | 35/35 (100%) | +3 pp |
| Output tokens, as the reader counts them (median) | 4,954 | 408 | -4,546 (-92%) |
| Stdout characters (all runs) | 36,281 | 3,122 | -33,159 (-91%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many tasks need attention? | `1` | 5/5 | 5/5 |
| Which task is blocked? Give its id only. | `T902` | 5/5 | 5/5 |
| Who owns task T901? Give the owner only. | `kimi` | 5/5 | 5/5 |
| How many tasks does the ledger hold in total, including any not listed? | `5` | 5/5 | 5/5 |
| Can this projection check whether a seat is actually running (runtime attention)? Answer yes or no. | `no` | 5/5 | 5/5 |
| Does this brief carry any authority over identity? Answer yes or no. | `no` | 5/5 | 5/5 |
| Could the task ledger be read? Answer yes or no. | `no` | 4/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora glance program --ledger-path /tmp/axi-bench-glance/tasks.json` (exit 0)

```
{
  "schema_version": "world-snapshot/v1",
  "projection_version": "subject-attention/v1",
  "snapshot_id": "ws_fcc48716dc4342dd4163e81b",
  "subject": "akashic-aurora-program",
  "generated_at": "2026-10-13T00:24:42.556911Z",
  "sources": [
    {
      "name": "task-ledger-git",
      "plane": "durable-ledger",
      "authority": "governed_source",
      "revision": "sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
      "checked_at": "2026-10-13T00:24:42.556911Z",
      "drill": "/tmp/axi-bench-glance/tasks.json"
    }
  ],
  "capabilities": {
    "arc_membership": {
      "state": "SUPPORTED",
      "basis": [
        "arcs:A1,A10,A11,A12,A13,A14,A15,A2,A3,A4,A5,A6,A7,A8,A9",
        "source:data/arcs-register/register.json@sha256:84ce5e544c9bc44e054506f5c62b8dd36e1132180212973689db3ec5f55d041e"
      ]
    },
    "artifact_authority": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the atom/projection authority adapter is not in slice one"
    },
    "deduplication": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "logical message identity is not yet authoritative"
    },
    "git_changes": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Git change adapter is not in slice one"
    },
    "lineage": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "complete original-to-redrive lineage is not yet authoritative"
    },
    "mail_state": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Bifrost plane adapter is not in slice one"
    },
    "operator_queue": {
      "state": "UNCHECKABLE",
      "blocked_by": "A15-operator-contract",
      "reason": "operator ownership and queue semantics are not yet settled substrate"
    },
    "runtime_attention": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "ledger workflow state does not prove a seat is live, aware, or acting"
    },
    "settlement": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "settlement cannot be inferred where outcome pointers are absent"
    },
    "subject_attention": {
      "state": "SUPPORTED",
      "basis": [
        "policy:task-status-attention/v1",
        "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137"
      ]
    },
    "task_state": {
      "state": "SUPPORTED",
      "basis": [
        "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137"
      ]
    },
    "test_receipts": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the verification receipt adapter is not in slice one"
    }
  },
  "summary": {
    "operator_sentence": "akashic-aurora-program ledger projection: 1 need attention, 1 acting, 1 waiting, 2 quiet; 5 total, 5 shown; 9 capabilities uncheckable.",
    "changed": [],
    "needs_attention": [
      "task:T902"
    ],
    "unknowns": [
      "artifact_authority",
      "deduplication",
      "git_changes",
      "lineage",
      "mail_state",
      "operator_queue",
      "runtime_attention",
      "settlement",
      "test_receipts"
    ]
  },
  "bounds": {
    "item_limit": 64,
    "total_items": 5,
    "returned_items": 5,
    "truncated": false
  },
  "items": [
    {
      "object_ref": "task:T902",
      "organ": "ledger",
      "attention": "ATTENTION",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T902",
        "title": "Retire the old bridge",
        "title_full_chars": 21,
        "title_truncated": false,
        "status": "blocked",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "claude",
        "deps": [
          "T901"
        ],
        "deps_total": 1,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": null,
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:42.556911Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "blocked",
          "basis": [
            {
              "ref": "field:task.status=blocked",
              "status": "recorded"
            }
          ]
        }
      }
    },
    {
      "object_ref": "task:T901",
      "organ": "ledger",
      "attention": "ACTING",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T901",
        "title": "Fence the migration path",
        "title_full_chars": 24,
        "title_truncated": false,
        "status": "in_progress",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "kimi",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [
          "core/a.py"
        ],
        "files_total": 1,
        "files_truncated": false,
        "commit": null,
        "arc": "A3"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:42.556911Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    },
    {
      "object_ref": "task:T905",
      "organ": "ledger",
      "attention": "WAITING",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T905",
        "title": "Approve the new seat",
        "title_full_chars": 20,
        "title_truncated": false,
        "status": "approved",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "claude",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": null,
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:42.556911Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    },
    {
      "object_ref": "task:T903",
      "organ": "ledger",
      "attention": "QUIET",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T903",
        "title": "Write the release notes",
        "title_full_chars": 23,
        "title_truncated": false,
        "status": "proposed",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": null,
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:42.556911Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    },
    {
      "object_ref": "task:T904",
      "organ": "ledger",
      "attention": "QUIET",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T904",
        "title": "Measure the recall latency",
        "title_full_chars": 26,
        "title_truncated": false,
        "status": "done",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "deepseek",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": "abc1234",
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:42.556911Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    }
  ],
  "projection_id": "gp_43a27f5b3f778767fad9209d",
  "render_id": "wr_ae5cb6d618929b03a0768112"
}
```

`aurora glance program --ledger-path /tmp/axi-bench-glance/tasks.json --max-items 2` (exit 0)

```
{
  "schema_version": "world-snapshot/v1",
  "projection_version": "subject-attention/v1",
  "snapshot_id": "ws_fcc48716dc4342dd4163e81b",
  "subject": "akashic-aurora-program",
  "generated_at": "2026-10-13T00:24:42.874277Z",
  "sources": [
    {
      "name": "task-ledger-git",
      "plane": "durable-ledger",
      "authority": "governed_source",
      "revision": "sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
      "checked_at": "2026-10-13T00:24:42.874277Z",
      "drill": "/tmp/axi-bench-glance/tasks.json"
    }
  ],
  "capabilities": {
    "arc_membership": {
      "state": "SUPPORTED",
      "basis": [
        "arcs:A1,A10,A11,A12,A13,A14,A15,A2,A3,A4,A5,A6,A7,A8,A9",
        "source:data/arcs-register/register.json@sha256:84ce5e544c9bc44e054506f5c62b8dd36e1132180212973689db3ec5f55d041e"
      ]
    },
    "artifact_authority": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the atom/projection authority adapter is not in slice one"
    },
    "deduplication": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "logical message identity is not yet authoritative"
    },
    "git_changes": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Git change adapter is not in slice one"
    },
    "lineage": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "complete original-to-redrive lineage is not yet authoritative"
    },
    "mail_state": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Bifrost plane adapter is not in slice one"
    },
    "operator_queue": {
      "state": "UNCHECKABLE",
      "blocked_by": "A15-operator-contract",
      "reason": "operator ownership and queue semantics are not yet settled substrate"
    },
    "runtime_attention": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "ledger workflow state does not prove a seat is live, aware, or acting"
    },
    "settlement": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "settlement cannot be inferred where outcome pointers are absent"
    },
    "subject_attention": {
      "state": "SUPPORTED",
      "basis": [
        "policy:task-status-attention/v1",
        "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137"
      ]
    },
    "task_state": {
      "state": "SUPPORTED",
      "basis": [
        "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137"
      ]
    },
    "test_receipts": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the verification receipt adapter is not in slice one"
    }
  },
  "summary": {
    "operator_sentence": "akashic-aurora-program ledger projection: 1 need attention, 1 acting, 1 waiting, 2 quiet; 5 total, 2 shown; 9 capabilities uncheckable.",
    "changed": [],
    "needs_attention": [
      "task:T902"
    ],
    "unknowns": [
      "artifact_authority",
      "deduplication",
      "git_changes",
      "lineage",
      "mail_state",
      "operator_queue",
      "runtime_attention",
      "settlement",
      "test_receipts"
    ]
  },
  "bounds": {
    "item_limit": 2,
    "total_items": 5,
    "returned_items": 2,
    "truncated": true
  },
  "items": [
    {
      "object_ref": "task:T902",
      "organ": "ledger",
      "attention": "ATTENTION",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T902",
        "title": "Retire the old bridge",
        "title_full_chars": 21,
        "title_truncated": false,
        "status": "blocked",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "claude",
        "deps": [
          "T901"
        ],
        "deps_total": 1,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": null,
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:42.874277Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "blocked",
          "basis": [
            {
              "ref": "field:task.status=blocked",
              "status": "recorded"
            }
          ]
        }
      }
    },
    {
      "object_ref": "task:T901",
      "organ": "ledger",
      "attention": "ACTING",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T901",
        "title": "Fence the migration path",
        "title_full_chars": 24,
        "title_truncated": false,
        "status": "in_progress",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "kimi",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [
          "core/a.py"
        ],
        "files_total": 1,
        "files_truncated": false,
        "commit": null,
        "arc": "A3"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:42.874277Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    }
  ],
  "projection_id": "gp_43a27f5b3f778767fad9209d",
  "render_id": "wr_587e24be7998624b9898f9e6"
}
```

`aurora glance program --ledger-path /tmp/axi-bench-glance/tasks.json --brief` (exit 0)

```
{
  "schema_version": "operational-brief/v1",
  "purpose": "operational_orientation",
  "identity_authority": "none",
  "snapshot_id": "ws_fcc48716dc4342dd4163e81b",
  "projection_id": "gp_43a27f5b3f778767fad9209d",
  "source_render_id": "wr_ae5cb6d618929b03a0768112",
  "subject": "akashic-aurora-program",
  "source_refs": [
    "task-ledger-git"
  ],
  "sources": [
    {
      "name": "task-ledger-git",
      "plane": "durable-ledger",
      "authority": "governed_source",
      "revision": "sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
      "checked_at": "2026-10-13T00:24:43.207948Z",
      "drill": "/tmp/axi-bench-glance/tasks.json"
    }
  ],
  "summary": {
    "operator_sentence": "akashic-aurora-program ledger projection: 1 need attention, 1 acting, 1 waiting, 2 quiet; 5 total, 5 shown; 9 capabilities uncheckable.",
    "changed": [],
    "needs_attention": [
      "task:T902"
    ],
    "unknowns": [
      "artifact_authority",
      "deduplication",
      "git_changes",
      "lineage",
      "mail_state",
      "operator_queue",
      "runtime_attention",
      "settlement",
      "test_receipts"
    ]
  },
  "capabilities": {
    "arc_membership": {
      "state": "SUPPORTED",
      "basis": [
        "arcs:A1,A10,A11,A12,A13,A14,A15,A2,A3,A4,A5,A6,A7,A8,A9",
        "source:data/arcs-register/register.json@sha256:84ce5e544c9bc44e054506f5c62b8dd36e1132180212973689db3ec5f55d041e"
      ]
    },
    "artifact_authority": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the atom/projection authority adapter is not in slice one"
    },
    "deduplication": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "logical message identity is not yet authoritative"
    },
    "git_changes": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Git change adapter is not in slice one"
    },
    "lineage": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "complete original-to-redrive lineage is not yet authoritative"
    },
    "mail_state": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Bifrost plane adapter is not in slice one"
    },
    "operator_queue": {
      "state": "UNCHECKABLE",
      "blocked_by": "A15-operator-contract",
      "reason": "operator ownership and queue semantics are not yet settled substrate"
    },
    "runtime_attention": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "ledger workflow state does not prove a seat is live, aware, or acting"
    },
    "settlement": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "settlement cannot be inferred where outcome pointers are absent"
    },
    "subject_attention": {
      "state": "SUPPORTED",
      "basis": [
        "policy:task-status-attention/v1",
        "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137"
      ]
    },
    "task_state": {
      "state": "SUPPORTED",
      "basis": [
        "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137"
      ]
    },
    "test_receipts": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the verification receipt adapter is not in slice one"
    }
  },
  "bounds": {
    "item_limit": 8,
    "available_items": 5,
    "returned_items": 5,
    "truncated": false,
    "source_snapshot_total": 5
  },
  "focus": [
    {
      "object_ref": "task:T902",
      "organ": "ledger",
      "attention": "ATTENTION",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T902",
        "title": "Retire the old bridge",
        "title_full_chars": 21,
        "title_truncated": false,
        "status": "blocked",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "claude",
        "deps": [
          "T901"
        ],
        "deps_total": 1,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": null,
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:43.207948Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "blocked",
          "basis": [
            {
              "ref": "field:task.status=blocked",
              "status": "recorded"
            }
          ]
        }
      }
    },
    {
      "object_ref": "task:T901",
      "organ": "ledger",
      "attention": "ACTING",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T901",
        "title": "Fence the migration path",
        "title_full_chars": 24,
        "title_truncated": false,
        "status": "in_progress",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "kimi",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [
          "core/a.py"
        ],
        "files_total": 1,
        "files_truncated": false,
        "commit": null,
        "arc": "A3"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:43.207948Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    },
    {
      "object_ref": "task:T905",
      "organ": "ledger",
      "attention": "WAITING",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T905",
        "title": "Approve the new seat",
        "title_full_chars": 20,
        "title_truncated": false,
        "status": "approved",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "claude",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": null,
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:43.207948Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    },
    {
      "object_ref": "task:T903",
      "organ": "ledger",
      "attention": "QUIET",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T903",
        "title": "Write the release notes",
        "title_full_chars": 23,
        "title_truncated": false,
        "status": "proposed",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": null,
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:43.207948Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    },
    {
      "object_ref": "task:T904",
      "organ": "ledger",
      "attention": "QUIET",
      "source_refs": [
        "task-ledger-git"
      ],
      "data": {
        "id": "T904",
        "title": "Measure the recall latency",
        "title_full_chars": 26,
        "title_truncated": false,
        "status": "done",
        "status_valid": true,
        "attention_basis": "policy:task-status-attention/v1",
        "owner": "deepseek",
        "deps": [],
        "deps_total": 0,
        "deps_truncated": false,
        "files": [],
        "files_total": 0,
        "files_truncated": false,
        "commit": "abc1234",
        "arc": "UNCLASSIFIED"
      },
      "epistemic_view": {
        "authority": {
          "value": "governed_source",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ]
        },
        "claim_kind": {
          "value": "inferred",
          "basis": [
            {
              "ref": "field:task.status",
              "status": "recorded"
            },
            {
              "ref": "policy:task-status-attention/v1",
              "status": "recorded"
            }
          ]
        },
        "currency": {
          "value": "current",
          "basis": [
            {
              "ref": "source:task-ledger-git@sha256:4036818cd507bde6312721aab27c0d54af796fec7e784e46913617311bf43137",
              "status": "recorded"
            }
          ],
          "checked_at": "2026-10-13T00:24:43.207948Z"
        },
        "identity_state": {
          "value": "unknown",
          "basis": []
        },
        "risk": {
          "value": "unknown",
          "basis": []
        }
      }
    }
  ],
  "brief_id": "ob_b3b9049501b0b5d424b843b3"
}
```

`aurora glance program --ledger-path /tmp/axi-bench-glance/nope.json` (exit 0)

```
{
  "schema_version": "world-snapshot/v1",
  "projection_version": "subject-attention/v1",
  "snapshot_id": "ws_5e7ca921bfe37d6634730222",
  "subject": "akashic-aurora-program",
  "generated_at": "2026-10-13T00:24:43.529226Z",
  "sources": [],
  "capabilities": {
    "arc_membership": {
      "state": "SUPPORTED",
      "basis": [
        "arcs:A1,A10,A11,A12,A13,A14,A15,A2,A3,A4,A5,A6,A7,A8,A9",
        "source:data/arcs-register/register.json@sha256:84ce5e544c9bc44e054506f5c62b8dd36e1132180212973689db3ec5f55d041e"
      ]
    },
    "artifact_authority": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the atom/projection authority adapter is not in slice one"
    },
    "deduplication": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "logical message identity is not yet authoritative"
    },
    "git_changes": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Git change adapter is not in slice one"
    },
    "lineage": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "complete original-to-redrive lineage is not yet authoritative"
    },
    "mail_state": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the Bifrost plane adapter is not in slice one"
    },
    "operator_queue": {
      "state": "UNCHECKABLE",
      "blocked_by": "A15-operator-contract",
      "reason": "operator ownership and queue semantics are not yet settled substrate"
    },
    "runtime_attention": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "ledger workflow state does not prove a seat is live, aware, or acting"
    },
    "settlement": {
      "state": "UNCHECKABLE",
      "blocked_by": "T116",
      "reason": "settlement cannot be inferred where outcome pointers are absent"
    },
    "subject_attention": {
      "state": "UNCHECKABLE",
      "blocked_by": "task_state",
      "reason": "attention requires readable task state"
    },
    "task_state": {
      "state": "UNCHECKABLE",
      "blocked_by": "task-ledger-git",
      "reason": "FileNotFoundError: [Errno 2] No such file or directory: '/tmp/axi-bench-glance/nope.json'"
    },
    "test_receipts": {
      "state": "UNCHECKABLE",
      "blocked_by": "adapter-not-wired",
      "reason": "the verification receipt adapter is not in slice one"
    }
  },
  "summary": {
    "operator_sentence": "akashic-aurora-program ledger projection: 0 need attention, 0 acting, 0 waiting, 0 quiet; 0 total, 0 shown; 11 capabilities uncheckable.",
    "changed": [],
    "needs_attention": [],
    "unknowns": [
      "artifact_authority",
      "deduplication",
      "git_changes",
      "lineage",
      "mail_state",
      "operator_queue",
      "runtime_attention",
      "settlement",
      "subject_attention",
      "task_state",
      "test_receipts"
    ]
  },
  "bounds": {
    "item_limit": 64,
    "total_items": 0,
    "returned_items": 0,
    "truncated": false
  },
  "items": [],
  "projection_id": "gp_03dcb5f75f82d0ef8687245c",
  "render_id": "wr_8dbfc19981464cf6fac55cfa"
}
```


## After: output

`aurora glance program --ledger-path /tmp/axi-bench-glance/tasks.json` (exit 0)

```
projection: snapshot
subject: akashic-aurora-program
ledger: read
summary: "akashic-aurora-program ledger projection: 1 need attention, 1 acting, 1 waiting, 2 quiet; 5 total, 5 shown; 9 capabilities uncheckable."
total: 5
needs_attention[1]: T902
tasks[5]{id,attention,status,owner,arc,title}:
  T902,ATTENTION,blocked,claude,UNCLASSIFIED,Retire the old bridge
  T901,ACTING,in_progress,kimi,A3,Fence the migration path
  T905,WAITING,approved,claude,UNCLASSIFIED,Approve the new seat
  T903,QUIET,proposed,null,UNCLASSIFIED,Write the release notes
  T904,QUIET,done,deepseek,UNCLASSIFIED,Measure the recall latency
checkable[3]: arc_membership,subject_attention,task_state
uncheckable[9]: artifact_authority,deduplication,git_changes,lineage,mail_state,operator_queue,runtime_attention,settlement,test_receipts
help[1]:
  uv run agent_cli.py glance program --json
```

`aurora glance program --ledger-path /tmp/axi-bench-glance/tasks.json --max-items 2` (exit 0)

```
projection: snapshot
subject: akashic-aurora-program
ledger: read
summary: "akashic-aurora-program ledger projection: 1 need attention, 1 acting, 1 waiting, 2 quiet; 5 total, 2 shown; 9 capabilities uncheckable."
total: 5
shown: 2
needs_attention[1]: T902
tasks[2]{id,attention,status,owner,arc,title}:
  T902,ATTENTION,blocked,claude,UNCLASSIFIED,Retire the old bridge
  T901,ACTING,in_progress,kimi,A3,Fence the migration path
checkable[3]: arc_membership,subject_attention,task_state
uncheckable[9]: artifact_authority,deduplication,git_changes,lineage,mail_state,operator_queue,runtime_attention,settlement,test_receipts
help[2]:
  uv run agent_cli.py glance program --json
  uv run agent_cli.py glance program --max-items 5
```

`aurora glance program --ledger-path /tmp/axi-bench-glance/tasks.json --brief` (exit 0)

```
projection: brief
subject: akashic-aurora-program
identity_authority: none
ledger: read
summary: "akashic-aurora-program ledger projection: 1 need attention, 1 acting, 1 waiting, 2 quiet; 5 total, 5 shown; 9 capabilities uncheckable."
total: 5
needs_attention[1]: T902
tasks[5]{id,attention,status,owner,arc,title}:
  T902,ATTENTION,blocked,claude,UNCLASSIFIED,Retire the old bridge
  T901,ACTING,in_progress,kimi,A3,Fence the migration path
  T905,WAITING,approved,claude,UNCLASSIFIED,Approve the new seat
  T903,QUIET,proposed,null,UNCLASSIFIED,Write the release notes
  T904,QUIET,done,deepseek,UNCLASSIFIED,Measure the recall latency
checkable[3]: arc_membership,subject_attention,task_state
uncheckable[9]: artifact_authority,deduplication,git_changes,lineage,mail_state,operator_queue,runtime_attention,settlement,test_receipts
help[1]:
  uv run agent_cli.py glance program --brief --json
```

`aurora glance program --ledger-path /tmp/axi-bench-glance/nope.json` (exit 0)

```
projection: snapshot
subject: akashic-aurora-program
ledger: "UNREADABLE: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/axi-bench-glance/nope.json'"
summary: "akashic-aurora-program ledger projection: 0 need attention, 0 acting, 0 waiting, 0 quiet; 0 total, 0 shown; 11 capabilities uncheckable."
total: 0
needs_attention: none
tasks: "none: the ledger was not read"
checkable[1]: arc_membership
uncheckable[11]: artifact_authority,deduplication,git_changes,lineage,mail_state,operator_queue,runtime_attention,settlement,subject_attention,task_state,test_receipts
help[1]:
  uv run agent_cli.py glance program --json
```
