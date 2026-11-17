# Scoring rubric

Two layers: the rule-based feed score (`scripts/score_feed.py`, title and company only) and the manual
rubric you apply after reading the posting. The feed score orders your reading. The manual score decides.

## Manual rubric (1 to 5, weighted average)

| Dimension | Weight | 5 | 3 | 1 |
|---|---|---|---|---|
| Skill fit, judged against `facts.md` | 30% | stack matches closely | about half matches | a basic requirement is missing |
| Speed to first pay | 25% | 1 to 2 weeks | 1 month | 2+ months or long process |
| Location and payment fit | 20% | open to the candidate's country, payout works | unclear | excluded, or payout impossible |
| Pay level | 15% | at or above target | within 25% below | far below |
| Legitimacy and terms | 10% | known employer, clear posting | little information | red flags, binding conditions |

Adjust the weights if the candidate's situation differs (a student may weight speed to pay lower and
learning higher). Write the change in the log header.

Thresholds: 4.0 and above apply; 3.0 to 3.9 apply if time allows; below 3.0 drop.

Binding conditions (a military-service clause, a night-shift mandate, a relocation date) lower the
legitimacy and terms row, not the skill fit row.

## Hard stops (drop before scoring)

- A hard requirement the candidate fails: minimum GPA, license, clearance, citizenship, degree field.
- The posting bans the tools the candidate works with.
- Red flags from `job_check.py`: fees to apply, chat-app-only contact, checks or crypto, early requests for
  ID or bank data.
- The posting is closed.

Encode repeatable hard stops in `score_config.json` as `company_penalties` or `negatives`, so the feed sorts
them to the bottom before you read them.

## Status vocabulary

`candidate` then `assessed` then `applied` then `test` then `interview` then `offer`. Side exits: `rejected`,
`silent` (no reply after about 21 days), `dropped` (closed, scored low, or the candidate declined).

## Learning loop

When a rejection reason is known, add one line to the log's "Lessons" section and, if it repeats, change a
rubric weight or a config rule. Example lesson shape: "Board X shows closed postings as open on its list
page; the apply page is the truth, so job_check fetches that one."
