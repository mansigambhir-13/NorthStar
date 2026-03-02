# The Priority Debt Problem

## The New Bottleneck

In the AI-native era, execution speed is no longer the bottleneck.

Tools like Cursor, Copilot, and Claude Code have collapsed the cost of writing software. A single developer can now ship in hours what used to take weeks. Teams build more features, faster, than at any point in the history of software engineering.

And yet — most teams are still building the wrong things.

The bottleneck has shifted from **"can we build it?"** to **"should we build it?"** Speed without direction is just organized waste.

## What Is Priority Debt?

**Priority Debt** is the cumulative cost of working on low-leverage tasks while high-leverage work remains undone.

Every sprint, every day, every hour — teams make implicit prioritization decisions. When those decisions are wrong, the cost is not a bug or a broken build. The cost is invisible: the high-leverage feature that was never built, the strategic initiative that slipped another quarter, the compounding advantage that a competitor captured instead.

Priority Debt is not about doing things badly. It is about doing the wrong things well.

### How Priority Debt Compounds

Priority Debt compounds silently. Unlike a failing test or a crashed server, there is no alarm. There is only the slow realization, months later, that the team shipped 47 features and moved the needle on zero of them.

The compounding works like this:

1. **Week 1:** Team picks a medium-leverage task over a high-leverage one. Small cost.
2. **Week 4:** The high-leverage task is still undone. The medium-leverage features created new maintenance burden. The cost of switching back has increased.
3. **Week 12:** Three months of medium-leverage work has reshaped the codebase, team habits, and user expectations around the wrong priorities. The high-leverage work now requires a rewrite.
4. **Week 24:** The window for the high-leverage opportunity has closed.

Every low-leverage feature shipped is a high-leverage feature not shipped.

## Comparison: Three Types of Debt

| Dimension | Technical Debt | Design Debt | Priority Debt |
|-----------|---------------|-------------|---------------|
| **Definition** | Shortcuts in code quality | Shortcuts in UX quality | Shortcuts in prioritization quality |
| **Visible?** | Eventually (bugs, slowdowns) | Eventually (user complaints) | Rarely (opportunity cost is invisible) |
| **Measured by** | Code complexity, test coverage | Usability scores, NPS | NorthStar PDS (Priority Debt Score) |
| **Accumulates when** | Team ships without refactoring | Team ships without user research | Team ships without leverage analysis |
| **Cost** | Slower future development | Worse user experience | Wrong product entirely |
| **Who notices** | Engineers | Designers, users | Nobody — until it is too late |
| **Existing tools** | SonarQube, CodeClimate | Hotjar, FullStory | **None (until NorthStar)** |

## Why No Existing Tool Measures This

**Jira / Linear / Asana** track task completion, not task leverage. A team can close 100 tickets and accumulate massive Priority Debt if those 100 tickets were all low-leverage work. These tools answer "what did we do?" but not "should we have done it?"

**OKR tools (Lattice, Ally.io, Gtmhub)** define objectives but do not connect them to daily work. There is a canyon between "Increase retention by 20%" written in an OKR tool and the actual pull requests being merged today. OKR tools answer "what do we want?" but not "are we actually working toward it?"

**Analytics tools (Amplitude, Mixpanel)** measure what users do after features ship. They cannot tell you, before you build, whether a feature is worth building. They answer "what happened?" but not "what should happen next?"

**AI coding tools (Cursor, Copilot)** accelerate execution but are direction-agnostic. They make you faster at building whatever you point them at — including the wrong thing. They answer "how do we build it?" but not "should we build it?"

NorthStar is the missing tool. It answers: **"Is the work you are doing right now the highest-leverage work you could be doing?"**

## The Priority Debt Score (PDS)

NorthStar quantifies Priority Debt as a single number: the **Priority Debt Score (PDS)**.

- **PDS 0-2000:** Healthy. Team is working on high-leverage tasks aligned with goals.
- **PDS 2000-5000:** Drifting. Some low-leverage work is displacing higher-leverage alternatives.
- **PDS 5000-8000:** Significant debt. Team is spending most time on low-leverage work.
- **PDS 8000-10000:** Critical. Team has lost alignment between daily work and strategic goals.

The PDS is calculated continuously, not quarterly. It updates as tasks are added, completed, or reprioritized. It is a living metric, not a retrospective one.
