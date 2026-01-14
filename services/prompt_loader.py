"""Prompt loader service for managing versioned agent prompts."""
from typing import Dict, Optional
from pathlib import Path
import yaml
from utils.logger import log_tool_call

# Prompt files directory
PROMPTS_DIR = Path(__file__).parent.parent / 'prompts'

# Cache for loaded prompts
_prompt_cache: Dict[str, Dict] = {}


def load_prompt_file(agent_name: str) -> Dict:
    """Load prompt YAML file for an agent.
    
    Args:
        agent_name: Name of the agent (e.g., "qa_agent", "router")
    
    Returns:
        Dictionary containing prompt versions and default version
    """
    cache_key = agent_name
    if cache_key in _prompt_cache:
        return _prompt_cache[cache_key]
    
    prompt_file = PROMPTS_DIR / f"{agent_name}.yaml"
    
    if not prompt_file.exists():
        error_msg = f"Prompt file not found: {prompt_file}"
        log_tool_call("prompt_loader", {"agent_name": agent_name, "error": error_msg})
        raise FileNotFoundError(error_msg)
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_data = yaml.safe_load(f)
        
        _prompt_cache[cache_key] = prompt_data
        log_tool_call("prompt_loader", {"agent_name": agent_name, "file": str(prompt_file)})
        return prompt_data
    except Exception as e:
        error_msg = f"Error loading prompt file {prompt_file}: {str(e)}"
        log_tool_call("prompt_loader", {"agent_name": agent_name, "error": error_msg})
        raise


def get_prompt(agent_name: str, version: Optional[str] = None) -> str:
    """Get prompt content for an agent.
    
    Args:
        agent_name: Name of the agent (e.g., "qa_agent", "router")
        version: Optional version to use (defaults to default_version in file)
    
    Returns:
        Prompt content as string
    """
    prompt_data = load_prompt_file(agent_name)
    
    # Determine which version to use
    if version is None:
        version = prompt_data.get('default_version', 'v1')
    
    # Get the version data
    versions = prompt_data.get('versions', {})
    if version not in versions:
        error_msg = f"Version '{version}' not found for agent '{agent_name}'"
        log_tool_call("prompt_loader", {"agent_name": agent_name, "version": version, "error": error_msg})
        # Fallback to default_version or v1
        version = prompt_data.get('default_version', 'v1')
        if version not in versions:
            raise ValueError(f"No valid version found for agent '{agent_name}'")
    
    version_data = versions[version]
    prompt_content = version_data.get('content', '')
    
    log_tool_call("prompt_loader", {
        "agent_name": agent_name,
        "version": version,
        "content_length": len(prompt_content)
    })
    
    return prompt_content.strip()


def list_available_versions(agent_name: str) -> Dict[str, Dict]:
    """List all available versions for an agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        Dictionary mapping version names to version metadata
    """
    prompt_data = load_prompt_file(agent_name)
    versions = prompt_data.get('versions', {})
    
    # Extract metadata for each version
    version_info = {}
    for version, data in versions.items():
        version_info[version] = {
            'description': data.get('description', ''),
            'created': data.get('created', ''),
            'content_length': len(data.get('content', ''))
        }
    
    return version_info


def get_default_version(agent_name: str) -> str:
    """Get the default version for an agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        Default version string
    """
    prompt_data = load_prompt_file(agent_name)
    return prompt_data.get('default_version', 'v1')


def reload_prompts():
    """Clear prompt cache to force reload from files."""
    global _prompt_cache
    _prompt_cache.clear()
    log_tool_call("prompt_loader", {"action": "cache_cleared"})


# List of available prompt files
AVAILABLE_PROMPTS = [
    "router",
    "qa_agent",
    "ordering_agent",
    "payment_agent",
    "cancellation_agent"
]
