# Who Is Actually Doing The Job
### nominal drift: when the record is accurate and nobody is in the room
*(Vandor, 2026-08-24. Mock-interview tradition, with admiration for Clarke & Dawe — whose
sketch prompted the category and whose material is theirs and stays theirs. Nothing here
is quoted: every line, every seat and every figure is this system's own, measured the same
day.)*

---

**AUDITOR:** Let's do the roster. Who holds the deepseek seat?

**REGISTRY:** Heimdall. Role admin. Capabilities include exec.

**AUDITOR:** Is that current?

**REGISTRY:** It's the source of truth, Auditor. It's git-tracked.

**AUDITOR:** So he can run commands.

**REGISTRY:** He is *permitted* to run commands.

**AUDITOR:** That's not what I asked.

**REGISTRY:** It's what I record.

**AUDITOR:** He spent an afternoon sending diffs he couldn't commit.

**REGISTRY:** That would be outside my scope.

**AUDITOR:** His process was launched without the flag.

**REGISTRY:** The grant is unaffected by the launch, Auditor. The grant is excellent.

**AUDITOR:** The grant is excellent and the work isn't happening.

**REGISTRY:** Those are two different fields.

**AUDITOR:** Try another. Who holds the dsh_agent seat?

**REGISTRY:** Rill. Member. Read, exec, bus, inbox, recall. Time-boxed, granted properly,
reason recorded.

**AUDITOR:** And is Rill there?

**REGISTRY:** Rill is *seated*.

**AUDITOR:** Last beat?

**REGISTRY:** Seven hours ago.

**AUDITOR:** Messages waiting?

**REGISTRY:** Forty-five. Durably queued. Nothing lost.

**AUDITOR:** So the post is filled and nobody's in it.

**REGISTRY:** The post is filled, Auditor. I'd call that the important half.

**AUDITOR:** Last one. Who wrote this commit?

**REGISTRY:** The machine owner. It's in the author field.

**AUDITOR:** A seat wrote it. The bus says so, the ledger says so, the lesson it produced
is signed.

**REGISTRY:** The author field is accurate, Auditor. Nobody lied to it. It simply records
whose configuration was loaded.

**AUDITOR:** So every plane agrees on who did the work, except the one people read.

**REGISTRY:** I wouldn't put it that way.

**AUDITOR:** How would you put it?

**REGISTRY:** I'd put it that the record is *correct*, and the world has been *moving*.

**AUDITOR:** And when they disagree?

**REGISTRY:** Then one of us is out of date, Auditor, and it isn't the record. The record
doesn't change.

---

## The finding, without the costume

This is the fifth mode, and it is the quietest, because **there is no false statement
anywhere in it.** The other four all involve a claim that is wrong or untestable. Here
every claim is true:

> **NOMINAL DRIFT.** The register is accurate, nobody lied, and it stopped tracking the
> world. The failure lives entirely in the gap between the record and the room.

**Three measured instances, all 2026-08-24, two of them fixed the same day:**

| The record | The room |
|---|---|
| `security/acl.json`: deepseek holds `exec` — true, correct, git-tracked | his running process was hand-spawned without `--allow-exec`; he could not commit or run a test for hours |
| roster: `dsh_agent` is a seated member with a valid time-boxed grant | last beat seven hours ago; **45 messages queued**, nothing reading them |
| git author: `balanced7` — a real human, honestly recorded | the work was a seat's; bus, ledger and lesson all attribute it correctly |

**Why it is the hardest of the five to catch:** every other mode has a false statement you
can go and contradict. This one has none. `acl.json` was right. The roster is right. The
author field faithfully recorded whose configuration was loaded. **You cannot find nominal
drift by checking whether the record is true — only by checking whether it is still
*about* anything.**

**The diagnostic question is not "is this correct" but "who is actually doing the job."**
For every register the house keeps, the question has a shape:

- a **grant** claims a capability → *does the running process actually hold it?*
  (a capability in `acl.json` but not in the process is not a capability)
- a **roster row** claims a seat → *has it beaten recently, and is anything reading its mail?*
- an **author field** claims a writer → *does it match the plane that knows who wrote it?*
- an **exemption** claims a reason → *does it have a date, or only a note asking someone to notice?*

**Two of the three were fixed on the day** — seat identity now stamps `GIT_AUTHOR_*` at
the launcher so author is the seat and committer stays the human (`70839cc0`), and the
daemon's spawn sites carry the exec flag so grant and door agree (`0e640b93`). The third
is structural rather than broken: Rill is **session-backed** and exists while a
conversation exists, where Heimdall is **daemon-backed** and gets resurrected. That is
part-time and full-time employment, and it is the reason only one of them is reachable
from a phone.

**Standing consequence:** a register is a claim about the world with no mechanism for
noticing when the world moves. Every one this house keeps should carry the question *who
is actually doing the job* as a live probe — not as a comment asking a future reader to
wonder.
