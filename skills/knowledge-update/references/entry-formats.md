# Entry formats

## MEMORY.md
One line per fact, under the right heading, present tense:

    - Invoice tax rate is passed in basis points (2000 = 20%).

## decisions.md
Append at the end of the file. Date is the day the decision was made (UTC).
Two spaces between date and title. All three lines are required.

    ## 2026-10-20  Release notes are written to docs/releases/
    Why: one place for humans to review before publishing. Ref: PR #12
    Supersedes: none

To reverse a decision, append a new entry:

    ## 2026-11-02  Release notes move to the CHANGELOG.md file
    Why: one file is easier to link. Ref: PR #31
    Supersedes: 2026-10-20 Release notes are written to docs/releases/

## SKILL.md "Known mistakes"
One bullet: the mistake, then what to do instead.

    - Squash merges hide co-authors. Read the PR body, not only the commit.
