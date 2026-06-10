# S2 API Sketch — Personas + Project Loader + Init

Review input for 5-expert gate. Implementation follows after BLOCKING=0.

## Design decisions

| Item | Decision |
|------|----------|
| jinja2 | Add `jinja2>=3.1` in S2 (init renders `.j2`; shared with S8 orchestrator later) |
| Bundled assets | Canonical edit at repo root; **runtime reads `src/agent_team/bundled/`** via package-data |
| Merge order | global → bundled → project (later overrides same `name`) |
| Init idempotency | Refuse if `TEAM.md` exists unless `--force` |
| Persona name validation | `safe_segment(name, "persona")` on load |

## Bundled layout

```
src/agent_team/bundled/
  personas/*.yaml          # copy of repo personas/
  templates/project/*.j2   # copy of templates/project/
  playbooks/*.yaml         # copy of docs/playbooks/
```

`bundled_paths.py` resolves via `importlib.resources.files("agent_team.bundled")`.

---

## `personas.py` — PersonaRegistry

### Persona dataclass

```python
@dataclass
class Persona:
    name: str
    cli: str
    description: str
    spawn_prompt_template: str
    model_hint: str | None = None
    tools_hint: str | None = None
    coordination_cli: list[str] | None = None
```

### PersonaRegistry

```python
class PersonaNotFoundError(LookupError): ...

class PersonaRegistry:
    def __init__(
        self,
        *,
        project_path: Path | None = None,
        global_dir: Path | None = None,
    ) -> None
        # global_dir default: Path.home() / ".agent-team" / "personas"

    def load_all(self) -> dict[str, Persona]
    def get(self, name: str) -> Persona
    def list_personas(self) -> list[Persona]
    def filter_allowed(self, allowed: list[str]) -> list[Persona]
    def is_allowed(self, name: str, allowed: list[str]) -> bool
```

### Merge layers (low → high priority)

1. `{global_dir}/*.yaml`
2. `bundled/personas/*.yaml`
3. `{project_path}/.agent-team/personas/*.yaml`

Missing dirs → skip. Invalid YAML → `PersonaLoadError`.

---

## `project_loader.py` — ProjectLoader

```python
@dataclass
class LeadContext:
    text: str
    config: dict
    playbook_name: str | None
    playbook: dict | None

class ProjectConfigError(ValueError): ...
class PlaybookNotFoundError(FileNotFoundError): ...

class ProjectLoader:
    def __init__(self, project_path: Path) -> None

    def load_config(self) -> dict
        # .agent-team/config.yaml; raises if missing

    def load_team_md(self) -> str
        # TEAM.md; raises if missing

    def load_playbook(self, name: str | None = None) -> dict
        # .agent-team/playbooks/{name}.yaml
        # name default: config["default_playbook"]

    def build_lead_context(
        self,
        *,
        playbook_name: str | None = None,
        extra_context: str | None = None,
    ) -> LeadContext
```

### `build_lead_context` assembly

```
--- TEAM.md ---
{team_md}

--- Project config ---
max_teammates: N
allowed_personas: [...]

--- Playbook: {name} ---
{yaml dump or summary}

--- Extra context ---
{extra_context}
```

---

## `cli/init.py` — agent-team init

```python
INIT_TEMPLATES: dict[str, dict] = {
    "fastapi": {
        "stack": "FastAPI + SQLAlchemy + pytest",
        "test_command": "pytest tests/ -q",
        "lint_command": "ruff check .",
        "branch": "main",
        "notes": "FastAPI service template",
    },
}

@click.command("init")
@click.option("--template", default="fastapi", type=click.Choice(list(INIT_TEMPLATES)))
@click.option("--project", type=click.Path(path_type=Path), default=".")
@click.option("--force", is_flag=True)
def init_cmd(template: str, project: Path, force: bool) -> None
```

### Init steps

1. `project = project.resolve()`
2. If `(project / "TEAM.md").exists()` and not `force` → exit 1 with message
3. Render `TEAM.md` from bundled `templates/project/TEAM.md.j2`
4. Render `.agent-team/config.yaml` from `config.yaml.j2`
5. Copy bundled `playbooks/*.yaml` → `.agent-team/playbooks/`
6. `mkdir .agent-team/personas` (empty)
7. Echo created paths

### Jinja context

| Variable | Source |
|----------|--------|
| `project_name` | `project.name` |
| `stack`, `test_command`, `lint_command`, `branch`, `notes` | `INIT_TEMPLATES[template]` |
| `forbidden_paths` | list from template preset |

---

## `pyproject.toml` changes

```toml
dependencies = [..., "jinja2>=3.1"]

[tool.setuptools.package-data]
agent_team = ["bundled/**/*"]
```

---

## Test matrix (9+)

| Test | Module |
|------|--------|
| bundled 4 personas load | personas |
| project yaml overrides bundled | personas |
| filter_allowed / is_allowed | personas |
| get unknown → PersonaNotFoundError | personas |
| load_config + load_team_md | project_loader |
| load_playbook default | project_loader |
| build_lead_context sections | project_loader |
| init creates TEAM.md + config + playbooks | init |
| init refuses without --force if exists | init |

---

## Downstream (S3+)

- S3 `personas list` → `PersonaRegistry.list_personas()`
- S3 `context show` → `ProjectLoader.build_lead_context()`
- S6 `list_personas` → `filter_allowed(config["allowed_personas"])`
- S5/S6 spawn → `is_allowed(persona, config["allowed_personas"])`
