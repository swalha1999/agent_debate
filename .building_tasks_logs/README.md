# `.building_tasks_logs/`

Build-process audit trail. **For every task we do while building this project, we
write one JSON file here recording the task's prompt and the tokens it used.**

This documents the AI-assisted development workflow and makes token/cost usage
visible per task — required by the lecturer's guidelines and our
`docs/Improvements_to_keep_in_mind.md` checklist.

> We track the **task** (its prompt) and the **tokens** — not the model's responses.
>
> Note: this is **build-time** logging (how the project was *made*). It is separate
> from the **runtime** LOG package (`packages/log`) that records what happens *inside*
> a debate.

## File naming

```
NNN-short-slug.json
```
- `NNN` = zero-padded sequence (`001`, `002`, …) in the order tasks were done.
- `slug` = kebab-case summary (e.g. `001-scaffold-workspace.json`).
- Map to `docs/TASKS.md` task IDs via the `task_id` field when applicable.

## Schema

See `_template.json`. Fields:

| Field | Meaning |
|---|---|
| `task_id` | TASKS.md id (e.g. `0.1`), or a label like `planning`/`docs`. |
| `title` | Short human title of the task. |
| `date` | `YYYY-MM-DD`. |
| `model` | Model that did the work (e.g. `claude-opus-4-8`). |
| `prompt` | The verbatim prompt that defined the task. |
| `tokens` | `{input, output, total}` for the task. |

## Relationship to the guideline-required artifacts

This folder is our **extra** granular log. The lecturer's guidelines additionally
require two things, which each task must also feed:

1. **Prompt Book — `docs/PROMPTS.md`** (guideline §8.3): roll *significant* prompts
   into the narrative prompt book (context, goal, output, lessons).
2. **Token cost table** (guideline §11.1): add the task's token counts to the
   cost-breakdown table (model · input · output · cost) — Epic 15 / `docs/PRD.md §10`.

So per task: write the JSON here **and** update the Prompt Book + cost table.

## Rules

- **One file per task.** Append, don't overwrite history.
- Record the **prompt** verbatim and the **token usage** — nothing else needed here.
- This folder **is** committed (it's documentation), so never put secrets/keys in it.
