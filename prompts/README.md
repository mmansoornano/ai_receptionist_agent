# Agent Prompts Directory

This directory contains system prompts for all agents in the multi-agent system.

## Structure

```
prompts/
├── README.md                    # This file
├── router.yaml                  # Router agent prompt
├── qa_agent.yaml                # QA/Product Inquiry agent prompt
├── ordering_agent.yaml          # Ordering/Cart agent prompt
├── payment_agent.yaml           # Payment agent prompt
└── cancellation_agent.yaml      # Cancellation agent prompt
```

## Versioning

Each prompt file uses YAML format with versioning support:

```yaml
versions:
  v1:
    content: |
      Your prompt text here...
    created: "2024-01-15"
    description: "Initial version"
  
  v2:
    content: |
      Updated prompt text...
    created: "2024-01-20"
    description: "Added product listing instructions"
  
default_version: v2
```

## Usage

Prompts are loaded by the `prompt_loader` service:

```python
from services.prompt_loader import get_prompt

# Get latest version
prompt = get_prompt("qa_agent")

# Get specific version
prompt = get_prompt("qa_agent", version="v1")
```

## Editing Prompts

1. **Edit the YAML file** for the agent you want to modify
2. **Create a new version** in the versions section
3. **Update default_version** to use the new version
4. **Add description** explaining what changed
5. **Test** the changes with the agent

## Best Practices

- Always create a new version when modifying prompts (don't edit existing versions)
- Add clear descriptions for each version
- Test changes before deploying
- Keep prompts focused and clear
- Use consistent formatting across prompts
