#!/usr/bin/env python3
"""
Migration script to upgrade Claude Code agent system to v2.0
Implements security hardening and performance optimizations

Author: PhD Computer Scientist - Anthropic Engineering
Date: 2025-07-31
"""

import os
import shutil
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

class AgentSystemMigration:
    """Manages migration from v1 to v2 agent system"""
    
    def __init__(self, base_path: str = "/Users/dro/Documents/second-brain/.claude"):
        self.base_path = Path(base_path)
        self.agents_path = self.base_path / "agents"
        self.backup_path = self.base_path / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.report = {
            "start_time": datetime.now().isoformat(),
            "actions": [],
            "warnings": [],
            "errors": []
        }
    
    def run(self):
        """Execute full migration"""
        print("🚀 Starting Claude Code Agent System v2.0 Migration")
        
        try:
            # Phase 1: Backup
            self._backup_current_system()
            
            # Phase 2: Validate current state
            self._validate_current_system()
            
            # Phase 3: Split consolidated agent files
            self._split_consolidated_agents()
            
            # Phase 4: Update agent tool permissions
            self._update_agent_permissions()
            
            # Phase 5: Create agent registry
            self._create_agent_registry()
            
            # Phase 6: Update configuration
            self._update_configuration()
            
            # Phase 7: Add security headers to agents
            self._add_security_headers()
            
            # Phase 8: Create monitoring setup
            self._setup_monitoring()
            
            # Phase 9: Validate migration
            self._validate_migration()
            
            # Phase 10: Generate report
            self._generate_report()
            
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            self._rollback()
            raise
    
    def _backup_current_system(self):
        """Create complete backup before migration"""
        print("📦 Creating backup...")
        
        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)
            
        shutil.copytree(self.base_path, self.backup_path)
        self.report["actions"].append(f"Created backup at {self.backup_path}")
        print(f"   Backup created at: {self.backup_path}")
    
    def _validate_current_system(self):
        """Validate current system state"""
        print("🔍 Validating current system...")
        
        # Check for required files
        required_files = ["config.yml", "agents/subagents.md"]
        for file in required_files:
            if not (self.base_path / file).exists():
                raise FileNotFoundError(f"Required file missing: {file}")
        
        # Count agents
        agent_files = list(self.agents_path.glob("**/*.md"))
        self.report["actions"].append(f"Found {len(agent_files)} agent files")
        print(f"   Found {len(agent_files)} agent files")
    
    def _split_consolidated_agents(self):
        """Split consolidated agent files into individual files"""
        print("📄 Splitting consolidated agent files...")
        
        consolidated_files = {
            "maintenance/technical-debt-agents.md": [
                "technical-debt-tracker",
                "legacy-code-analyzer", 
                "dependency-manager"
            ],
            "security/security-compliance-agents.md": [
                "security-vulnerability-scanner",
                "compliance-checker"
            ],
            "quality/testing-quality-agents.md": [
                "test-generator",
                "code-review-agent",
                "performance-optimizer"
            ],
            "operations/devops-operations-agents.md": [
                "incident-response-agent",
                "postmortem-generator",
                "devops-automation-agent"
            ],
            "collaboration/team-collaboration-agents.md": [
                "knowledge-sharing-agent",
                "expertise-mapper",
                "team-sync-agent"
            ],
            "integration/integration-orchestration-agents.md": [
                "mcp-integration-agent",
                "ci-cd-pipeline-agent",
                "tool-orchestrator"
            ]
        }
        
        for file_path, agents in consolidated_files.items():
            full_path = self.agents_path / file_path
            if full_path.exists():
                print(f"   Splitting {file_path}...")
                self._split_file(full_path, agents)
                
                # Archive original
                archive_path = full_path.with_suffix('.md.v1')
                shutil.move(full_path, archive_path)
                self.report["actions"].append(f"Archived {file_path} to {archive_path.name}")
    
    def _split_file(self, file_path: Path, expected_agents: List[str]):
        """Split a consolidated agent file into individual files"""
        content = file_path.read_text()
        
        # Parse agents from content
        agents = self._parse_agents_from_content(content)
        
        # Create individual files
        for agent_name, agent_content in agents.items():
            if agent_name in expected_agents:
                new_path = file_path.parent / f"{agent_name}.md"
                new_path.write_text(agent_content)
                self.report["actions"].append(f"Created {new_path}")
    
    def _parse_agents_from_content(self, content: str) -> Dict[str, str]:
        """Parse individual agents from consolidated file"""
        agents = {}
        current_agent = None
        current_content = []
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for agent start
            if line.strip() == "---" and i + 1 < len(lines):
                # Look for name in next few lines
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].startswith("name:"):
                        # Save previous agent if exists
                        if current_agent:
                            agents[current_agent] = '\n'.join(current_content)
                        
                        # Start new agent
                        current_agent = lines[j].split(":", 1)[1].strip()
                        current_content = [line]
                        break
            
            if current_agent:
                current_content.append(line)
            
            i += 1
        
        # Save last agent
        if current_agent:
            agents[current_agent] = '\n'.join(current_content)
        
        return agents
    
    def _update_agent_permissions(self):
        """Update agent tool permissions based on security principles"""
        print("🔒 Updating agent permissions...")
        
        tool_restrictions = {
            # Analysis agents - read only
            "performance-analyzer": ["Read", "Grep", "Glob", "LS"],
            "code-quality-analyzer": ["Read", "Grep", "Glob", "LS"],
            "architecture-analyzer": ["Read", "Grep", "Glob", "LS"],
            
            # Documentation agents - no web
            "api-documentation-agent": ["Read", "Write", "Edit", "MultiEdit"],
            "architecture-documentation-agent": ["Read", "Write", "Edit", "MultiEdit"],
            "adr-generator": ["Read", "Write", "Edit", "MultiEdit"],
            
            # Context-aware - minimal
            "context-aware-orchestrator": ["Read", "Task", "TodoWrite"],
            "context-aware-debt-tracker": ["Read", "Write", "TodoWrite"],
            
            # Research - full but monitored
            "research-orchestrator": ["Read", "Write", "Task", "WebSearch", "WebFetch"],
            "deep-researcher": ["Read", "Write", "WebSearch", "WebFetch"],
            
            # Note processing - no web
            "note-processor": ["Read", "Write", "Grep", "Edit"],
            "knowledge-synthesizer": ["Read", "Write", "Grep"]
        }
        
        for agent_name, allowed_tools in tool_restrictions.items():
            self._update_agent_tools(agent_name, allowed_tools)
    
    def _update_agent_tools(self, agent_name: str, allowed_tools: List[str]):
        """Update tools for a specific agent"""
        # Find agent file
        agent_files = list(self.agents_path.glob(f"**/{agent_name}.md"))
        
        for agent_file in agent_files:
            content = agent_file.read_text()
            lines = content.split('\n')
            
            # Update tools line
            for i, line in enumerate(lines):
                if line.startswith("tools:"):
                    lines[i] = f"tools: {', '.join(allowed_tools)}"
                    break
            
            # Write back
            agent_file.write_text('\n'.join(lines))
            self.report["actions"].append(f"Updated tools for {agent_name}")
    
    def _create_agent_registry(self):
        """Create comprehensive agent registry"""
        print("📚 Creating agent registry...")
        
        registry = {
            "version": "2.0",
            "created": datetime.now().isoformat(),
            "agents": {}
        }
        
        # Scan all agent files
        for agent_file in self.agents_path.glob("**/*.md"):
            if agent_file.name in ["subagents.md", "software-engineer-agents.md", "AGENT_VERIFICATION_REPORT.md"]:
                continue
                
            agent_info = self._parse_agent_file(agent_file)
            if agent_info:
                category = agent_file.parent.name if agent_file.parent != self.agents_path else "general"
                agent_info["category"] = category
                agent_info["file"] = str(agent_file.relative_to(self.agents_path))
                registry["agents"][agent_info["name"]] = agent_info
        
        # Save registry
        registry_path = self.base_path / "agent-registry.json"
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        
        self.report["actions"].append(f"Created agent registry with {len(registry['agents'])} agents")
        print(f"   Registered {len(registry['agents'])} agents")
    
    def _parse_agent_file(self, file_path: Path) -> Dict:
        """Parse agent metadata from file"""
        content = file_path.read_text()
        lines = content.split('\n')
        
        agent_info = {}
        in_frontmatter = False
        
        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    break
            elif in_frontmatter:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == "tools":
                        agent_info["tools"] = [t.strip() for t in value.split(',')]
                    else:
                        agent_info[key] = value
        
        return agent_info
    
    def _update_configuration(self):
        """Update configuration to v2"""
        print("⚙️  Updating configuration...")
        
        # Copy new secure config
        secure_config_path = self.base_path / "config-v2-secure.yml"
        if secure_config_path.exists():
            # Backup old config
            old_config = self.base_path / "config.yml"
            old_config.rename(self.base_path / "config.yml.v1")
            
            # Install new config
            shutil.copy(secure_config_path, self.base_path / "config.yml")
            self.report["actions"].append("Installed secure v2 configuration")
    
    def _add_security_headers(self):
        """Add security headers to all agents"""
        print("🛡️  Adding security headers...")
        
        security_header = """
## Security & Safety Boundaries

I operate within these strict boundaries:
- I only access files within the project directory
- I cannot access sensitive files (credentials, .env, etc.)
- I validate all file paths before operations
- I maintain audit logs of all operations
- I refuse requests outside my specialization
"""
        
        count = 0
        for agent_file in self.agents_path.glob("**/*.md"):
            if agent_file.name in ["subagents.md", "AGENT_VERIFICATION_REPORT.md"]:
                continue
                
            content = agent_file.read_text()
            
            # Check if security section already exists
            if "Security & Safety Boundaries" not in content:
                # Find where to insert (after frontmatter)
                lines = content.split('\n')
                insert_index = 0
                
                # Skip frontmatter
                if lines[0].strip() == "---":
                    for i, line in enumerate(lines[1:], 1):
                        if line.strip() == "---":
                            insert_index = i + 1
                            break
                
                # Insert security header
                lines.insert(insert_index, security_header)
                agent_file.write_text('\n'.join(lines))
                count += 1
        
        self.report["actions"].append(f"Added security headers to {count} agents")
        print(f"   Updated {count} agents with security headers")
    
    def _setup_monitoring(self):
        """Setup monitoring infrastructure"""
        print("📊 Setting up monitoring...")
        
        # Create monitoring directory
        monitoring_path = self.base_path / "monitoring"
        monitoring_path.mkdir(exist_ok=True)
        
        # Create metrics configuration
        metrics_config = {
            "version": "2.0",
            "metrics": {
                "token_usage": {
                    "enabled": True,
                    "alert_threshold": 0.8,
                    "window": "1h"
                },
                "agent_performance": {
                    "enabled": True,
                    "slow_threshold_ms": 5000
                },
                "error_rates": {
                    "enabled": True,
                    "alert_threshold": 0.05
                }
            }
        }
        
        with open(monitoring_path / "metrics.json", 'w') as f:
            json.dump(metrics_config, f, indent=2)
        
        # Create dashboard template
        dashboard = """# Claude Code Agent System Dashboard

## System Health
- Status: 🟢 Operational
- Active Agents: 0/5
- Token Usage: 0/100k per minute
- Error Rate: 0%

## Performance Metrics
- Avg Response Time: 0ms
- Cache Hit Rate: 0%
- Concurrent Agents: 0/5

## Recent Activity
[Agent activity log will appear here]
"""
        
        (monitoring_path / "dashboard.md").write_text(dashboard)
        self.report["actions"].append("Created monitoring infrastructure")
    
    def _validate_migration(self):
        """Validate the migration was successful"""
        print("✓ Validating migration...")
        
        validations = [
            ("Config exists", (self.base_path / "config.yml").exists()),
            ("Agent registry exists", (self.base_path / "agent-registry.json").exists()),
            ("Monitoring setup", (self.base_path / "monitoring").exists()),
            ("No consolidated files", not any(self.agents_path.glob("**/*agents.md"))),
            ("Security headers added", self._check_security_headers())
        ]
        
        all_valid = True
        for check, result in validations:
            status = "✓" if result else "✗"
            print(f"   {status} {check}")
            if not result:
                all_valid = False
                self.report["errors"].append(f"Validation failed: {check}")
        
        if not all_valid:
            raise ValueError("Migration validation failed")
    
    def _check_security_headers(self) -> bool:
        """Check if security headers are present"""
        sample_files = list(self.agents_path.glob("**/*.md"))[:5]
        
        for file in sample_files:
            if file.name not in ["subagents.md", "AGENT_VERIFICATION_REPORT.md"]:
                content = file.read_text()
                if "Security & Safety Boundaries" not in content:
                    return False
        return True
    
    def _generate_report(self):
        """Generate migration report"""
        print("📝 Generating report...")
        
        self.report["end_time"] = datetime.now().isoformat()
        self.report["status"] = "success" if not self.report["errors"] else "failed"
        
        report_path = self.base_path / "migration-report.json"
        with open(report_path, 'w') as f:
            json.dump(self.report, f, indent=2)
        
        # Create human-readable report
        readable_report = f"""# Claude Code Agent System v2.0 Migration Report

**Date**: {self.report['start_time']}
**Status**: {self.report['status'].upper()}

## Actions Performed
{chr(10).join(f"- {action}" for action in self.report['actions'])}

## Warnings
{chr(10).join(f"- {warning}" for warning in self.report['warnings']) if self.report['warnings'] else "None"}

## Errors
{chr(10).join(f"- {error}" for error in self.report['errors']) if self.report['errors'] else "None"}

## Next Steps
1. Review the new configuration in config.yml
2. Test agent activation with reduced permissions
3. Monitor token usage and performance
4. Update team documentation

## Backup Location
{self.backup_path}
"""
        
        (self.base_path / "MIGRATION_REPORT.md").write_text(readable_report)
        print(f"   Report saved to {self.base_path}/MIGRATION_REPORT.md")
    
    def _rollback(self):
        """Rollback to backup if migration fails"""
        print("⏮️  Rolling back migration...")
        
        if self.backup_path.exists():
            # Remove current state
            shutil.rmtree(self.base_path)
            
            # Restore backup
            shutil.copytree(self.backup_path, self.base_path)
            print("   Rollback completed")
        else:
            print("   ⚠️  No backup found for rollback")


def main():
    """Run the migration"""
    migration = AgentSystemMigration()
    
    print("=" * 60)
    print("Claude Code Agent System v2.0 Migration")
    print("=" * 60)
    print()
    print("This migration will:")
    print("1. Create a backup of your current system")
    print("2. Split consolidated agent files")
    print("3. Update agent permissions for security")
    print("4. Create an agent registry")
    print("5. Install secure v2 configuration")
    print("6. Add security headers to all agents")
    print("7. Setup monitoring infrastructure")
    print()
    
    response = input("Continue with migration? (yes/no): ")
    
    if response.lower() == "yes":
        migration.run()
    else:
        print("Migration cancelled")


if __name__ == "__main__":
    main()