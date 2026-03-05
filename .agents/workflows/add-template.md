---
description: Scaffold a new workflow template — create markdown file, register in gallery
---

## Prerequisites

- The project is installed (`pip install -e ".[dev]"`)
- You know the template slug (e.g., `data-pipeline`, `onboarding`, `deployment`)

## Steps

1. **Create the template file** at `templates/<slug>.md` using this structure:

```markdown
# <Template Title>

## Goal
<One-sentence goal of this workflow>

## Inputs
| Variable | Description | Example |
|---|---|---|
| `{{team}}` | Team responsible | Platform |
| `{{service}}` | Target service | payments-api |

## Workflow
- [ ] Step 1: <First action>
- [ ] Step 2: <Second action>
- [ ] Step 3: <Third action>
- [ ] Step 4: <Final action / notification>

## Outputs
- <What this workflow produces>

## KPIs
| Metric | Target |
|---|---|
| <metric name> | <target value> |
```

1. **Register in the gallery** — open `templates/gallery.py` and add a new `TemplateEntry` in the `_TEMPLATES` list inside the `get_gallery()` function:

```python
TemplateEntry(
    name="<slug>",
    description="<one-line description>",
    path=_TEMPLATE_DIR / "<slug>.md",
    tags=["<domain>"],
    variables=["team", "service"],
),
```

1. **Verify the template loads correctly**:

```bash
python -c "from templates.gallery import get_gallery; t = get_gallery().get('<slug>'); print(t.name, '-', t.description)"
```

1. **Update `README.md`** — add the new template to the "Core concepts → Workflows" table.

2. **Update `examples/README.md`** — add a row to the Examples Matrix table.

## Success criteria

- `templates/<slug>.md` exists with Goal, Inputs, Workflow, Outputs, KPIs sections
- Gallery loads the template without errors
- Template renders with variables correctly
- README and Examples Matrix updated
