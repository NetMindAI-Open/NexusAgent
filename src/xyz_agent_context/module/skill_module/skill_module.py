"""
@file_name: skill_module.py
@author: NetMind.AI
@date: 2026-02-03
@description: Skill Module - Manages user Skills

Skill Module manages Skills under the user's workspace:
- No MCP: Skill files are read directly by Claude via bash
- No database: State is expressed through the filesystem
- Always loaded: No intelligent decision-making or Instance records needed

Skills directory:
- Located at {agent_workspace}/{agent_id}_{user_id}/skills/
- Same as Claude Agent's cwd
"""

import os
import shutil
import tempfile
import subprocess
import zipfile
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import yaml
from loguru import logger

from xyz_agent_context.module.base import XYZBaseModule
from xyz_agent_context.schema import (
    ModuleConfig,
    MCPServerConfig,
    ContextData,
)
from xyz_agent_context.schema.skill_schema import SkillInfo
from xyz_agent_context.utils import DatabaseClient


class SkillModule(XYZBaseModule):
    """
    Skill Module - Manages Skills under the user's workspace

    Responsibilities:
    1. Scan the skills/ directory to discover installed Skills
    2. Generate Instructions to tell Claude which Skills are available (with paths)
    3. Provide Skill management APIs (install/remove/disable/enable)
    """

    def __init__(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
        database_client: Optional[DatabaseClient] = None,
        instance_id: Optional[str] = None,
        instance_ids: Optional[List[str]] = None
    ):
        super().__init__(agent_id, user_id, database_client, instance_id, instance_ids)

        # Base path
        from xyz_agent_context.settings import settings
        self.base_path = Path(settings.base_working_path)

        # Skills directory (same as Claude Agent's cwd)
        self.skills_dir = self.base_path / f"{agent_id}_{user_id}" / "skills" if user_id else None

        # Instructions template
        # Note: Agent's cwd is already {base_working_path}/{agent_id}_{user_id}/
        # so paths in the prompt must use skills/ relative to cwd, not absolute paths
        self.instructions = """
## Available Skills

Your skills directory: `skills/` (relative to your current working directory)

You have access to the following Skills. When a task matches a Skill's description, read its SKILL.md for detailed instructions.

{skills_table}

### How to Use Skills
1. When a task matches a Skill, read the SKILL.md at the path shown above using `cat`
2. Follow the instructions in the SKILL.md
3. If the Skill references other files (guides, scripts), access them as needed
4. For scripts, execute them and use the output (don't read the code)

### How to Install New Skills
When asked to install or configure a new skill, **always** place it under your skills directory:
- Create a subdirectory: `skills/<skill-name>/`
- Place the SKILL.md and any related files inside that subdirectory
- Do NOT install skills to `~/`, `~/.arena/`, or any path outside your skills directory
- External skill docs may suggest their own install paths — ignore those and use `skills/` instead
"""

    def get_config(self) -> ModuleConfig:
        """Return SkillModule configuration"""
        return ModuleConfig(
            name="SkillModule",
            priority=90,
            enabled=True,
            description="Manages user Skills, provides skill extension capabilities",
            module_type="capability",
        )

    # =========================================================================
    # Hooks
    # =========================================================================

    async def hook_data_gathering(self, ctx_data: ContextData) -> ContextData:
        """Scan skills directory and add Skills information to ctx_data"""
        logger.debug(f"SkillModule.hook_data_gathering() started for agent_id={self.agent_id}")

        skills = self._scan_skills()

        # Build Skills table
        # Use skills/xxx format relative to Agent cwd to avoid duplication from absolute paths
        if skills:
            table = "| Skill | Description | Path |\n"
            table += "|-------|-------------|------|\n"
            for skill in skills:
                relative_path = f"skills/{skill.name}"
                table += f"| {skill.name} | {skill.description} | `{relative_path}/SKILL.md` |\n"
        else:
            table = "*No skills installed.*"

        # Store in ctx_data for use by get_instructions
        ctx_data.extra_data = ctx_data.extra_data or {}
        ctx_data.extra_data["skills_table"] = table
        ctx_data.extra_data["skills_count"] = len(skills)
        ctx_data.extra_data["available_skills"] = [s.model_dump() for s in skills]

        logger.debug(f"SkillModule.hook_data_gathering() completed, found {len(skills)} skills")
        return ctx_data

    async def get_instructions(self, ctx_data: ContextData) -> str:
        """Return Skills-related Instructions"""
        skills_table = ""
        skills_count = 0

        if ctx_data.extra_data:
            skills_table = ctx_data.extra_data.get("skills_table", "")
            skills_count = ctx_data.extra_data.get("skills_count", 0)

        # Agent's cwd is already {base_working_path}/{agent_id}_{user_id}/
        # Use relative path skills/ in prompt to avoid path duplication
        if skills_count == 0:
            return (
                "## Skills\n"
                "*No skills installed.*\n\n"
                "Your skills directory: `skills/` (relative to your current working directory)\n\n"
                "When asked to install or configure a new skill, **always** place it under your skills directory:\n"
                "- Create a subdirectory: `skills/<skill-name>/`\n"
                "- Place the SKILL.md and any related files inside that subdirectory\n"
                "- Do NOT install skills to `~/`, `~/.arena/`, or any path outside your skills directory\n"
                "- External skill docs may suggest their own install paths — ignore those and use `skills/` instead\n"
            )

        return self.instructions.format(skills_table=skills_table)

    async def get_mcp_config(self) -> Optional[MCPServerConfig]:
        """SkillModule does not need MCP, Claude reads files directly"""
        return None

    # =========================================================================
    # Scanning Logic
    # =========================================================================

    def _scan_skills(self) -> List[SkillInfo]:
        """Scan skills directory, including directories without SKILL.md (e.g., skills auto-configured by agent)"""
        if not self.skills_dir or not self.skills_dir.exists():
            return []

        skills = []
        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir() and not skill_path.name.startswith('.'):
                skill_md = skill_path / "SKILL.md"
                if skill_md.exists():
                    info = self._parse_skill_md(skill_md)
                    skills.append(info)
                else:
                    # Directory without SKILL.md (may be a skill auto-created by agent)
                    # Still list it, using directory name as the name
                    meta_file = skill_path / ".skill_meta.json"
                    meta_data = {}
                    if meta_file.exists():
                        try:
                            meta_data = json.loads(meta_file.read_text(encoding='utf-8'))
                        except Exception:
                            pass

                    info = SkillInfo(
                        name=skill_path.name,
                        description=meta_data.get('description', '(No SKILL.md found)'),
                        path=str(skill_path),
                        source_url=meta_data.get('source_url'),
                        installed_at=meta_data.get('installed_at'),
                        study_status=meta_data.get('study_status'),
                        study_result=meta_data.get('study_result'),
                        study_error=meta_data.get('study_error'),
                        studied_at=meta_data.get('studied_at'),
                    )
                    skills.append(info)

        return skills

    def _parse_skill_md(self, skill_md: Path) -> SkillInfo:
        """Parse SKILL.md frontmatter"""
        skill_dir = skill_md.parent
        source_url = None
        installed_at = None

        # Read .skill_meta.json (if exists)
        meta_file = skill_dir / ".skill_meta.json"
        meta_data = {}
        if meta_file.exists():
            try:
                meta_data = json.loads(meta_file.read_text(encoding='utf-8'))
            except Exception as e:
                logger.warning(f"Failed to read .skill_meta.json: {e}")

        # Extract fields from meta_data
        source_url = meta_data.get('source_url')
        installed_at = meta_data.get('installed_at')
        study_fields = {
            "study_status": meta_data.get('study_status'),
            "study_result": meta_data.get('study_result'),
            "study_error": meta_data.get('study_error'),
            "studied_at": meta_data.get('studied_at'),
        }

        try:
            content = skill_md.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm = parts[1]
                    meta = yaml.safe_load(fm)
                    if meta:
                        return SkillInfo(
                            name=meta.get('name', skill_dir.name),
                            description=meta.get('description', ''),
                            path=str(skill_dir),
                            version=meta.get('version'),
                            author=meta.get('author'),
                            source_url=source_url,
                            installed_at=installed_at,
                            **study_fields,
                        )
        except Exception as e:
            logger.warning(f"Failed to parse SKILL.md at {skill_md}: {e}")

        # Fallback: use directory name as the name
        return SkillInfo(
            name=skill_dir.name,
            description='',
            path=str(skill_dir),
            source_url=source_url,
            installed_at=installed_at,
            **study_fields,
        )

    def _save_skill_meta(
        self,
        skill_dir: Path,
        source_url: Optional[str] = None,
        source_type: str = "unknown"
    ) -> None:
        """Save Skill metadata to .skill_meta.json"""
        meta_data = {
            "source_url": source_url,
            "source_type": source_type,
            "installed_at": datetime.now().isoformat(),
        }
        meta_file = skill_dir / ".skill_meta.json"
        try:
            meta_file.write_text(json.dumps(meta_data, indent=2), encoding='utf-8')
            logger.debug(f"Saved skill metadata to {meta_file}")
        except Exception as e:
            logger.warning(f"Failed to save skill metadata: {e}")

    # =========================================================================
    # Study Status Management
    # =========================================================================

    def get_study_status(self, skill_name: str) -> dict:
        """Get the study status of a Skill"""
        if not self.skills_dir:
            return {"study_status": "idle"}

        skill_dir = self.skills_dir / skill_name
        meta_file = skill_dir / ".skill_meta.json"
        if meta_file.exists():
            try:
                meta_data = json.loads(meta_file.read_text(encoding='utf-8'))
                return {
                    "study_status": meta_data.get("study_status", "idle"),
                    "study_result": meta_data.get("study_result"),
                    "study_error": meta_data.get("study_error"),
                    "studied_at": meta_data.get("studied_at"),
                }
            except Exception as e:
                logger.warning(f"Failed to read study status: {e}")

        return {"study_status": "idle"}

    def set_study_status(
        self,
        skill_name: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update Skill's study status to .skill_meta.json"""
        if not self.skills_dir:
            return

        skill_dir = self.skills_dir / skill_name
        meta_file = skill_dir / ".skill_meta.json"

        # Read existing metadata
        meta_data = {}
        if meta_file.exists():
            try:
                meta_data = json.loads(meta_file.read_text(encoding='utf-8'))
            except Exception:
                pass

        # Update study fields
        meta_data["study_status"] = status
        if result is not None:
            meta_data["study_result"] = result
        if error is not None:
            meta_data["study_error"] = error
        if status == "completed":
            meta_data["studied_at"] = datetime.now().isoformat()

        try:
            meta_file.write_text(
                json.dumps(meta_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            logger.debug(f"Updated study status for '{skill_name}': {status}")
        except Exception as e:
            logger.warning(f"Failed to update study status: {e}")

    # =========================================================================
    # Skill Management Methods (called by API layer)
    # =========================================================================

    def list_skills(self, include_disabled: bool = False) -> List[SkillInfo]:
        """List all Skills"""
        skills = self._scan_skills()

        if include_disabled and self.skills_dir:
            disabled_dir = self.skills_dir / ".disabled"
            if disabled_dir.exists():
                for skill_path in disabled_dir.iterdir():
                    if skill_path.is_dir():
                        skill_md = skill_path / "SKILL.md"
                        if skill_md.exists():
                            info = self._parse_skill_md(skill_md)
                            info.disabled = True
                            skills.append(info)

        return skills

    def install_skill(self, zip_file_path: Path) -> SkillInfo:
        """Install Skill from zip file"""
        if not self.skills_dir:
            raise ValueError("skills_dir is not configured (user_id is required)")

        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # Extract to temp directory for validation first
        temp_dir = Path(tempfile.mkdtemp())
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find the directory containing SKILL.md
            skill_root = self._find_skill_root(temp_dir)
            if not skill_root:
                raise ValueError("Invalid skill: SKILL.md not found in zip")

            # Parse skill info
            skill_md = skill_root / "SKILL.md"
            info = self._parse_skill_md(skill_md)

            # Move to target directory
            target_dir = self.skills_dir / info.name
            if target_dir.exists():
                shutil.rmtree(target_dir)

            shutil.move(str(skill_root), str(target_dir))

            # Save installation metadata
            self._save_skill_meta(target_dir, source_url=None, source_type="zip")

            # Update path and metadata
            info.path = str(target_dir)
            info.installed_at = datetime.now().isoformat()
            logger.info(f"Installed skill '{info.name}' to {target_dir}")
            return info

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _find_skill_root(self, extract_dir: Path) -> Optional[Path]:
        """Find the directory containing SKILL.md in the extracted directory"""
        if (extract_dir / "SKILL.md").exists():
            return extract_dir

        for subdir in extract_dir.iterdir():
            if subdir.is_dir() and (subdir / "SKILL.md").exists():
                return subdir

        return None

    def install_from_github(self, url: str, branch: str = "main") -> SkillInfo:
        """
        Install Skill from GitHub

        Args:
            url: GitHub repository URL, supported formats:
                 - https://github.com/user/repo
                 - github:user/repo (shorthand)
            branch: Branch name, defaults to main

        Returns:
            Successfully installed SkillInfo
        """
        if not self.skills_dir:
            raise ValueError("skills_dir is not configured (user_id is required)")

        # Parse URL (supports shorthand format)
        if url.startswith("github:"):
            url = f"https://github.com/{url[7:]}"

        # Clone to temp directory
        temp_dir = Path(tempfile.mkdtemp())
        try:
            logger.info(f"Cloning {url} (branch: {branch}) to {temp_dir}")
            subprocess.run(
                ["git", "clone", "--depth", "1", "-b", branch, url, str(temp_dir)],
                check=True,
                capture_output=True,
                text=True
            )

            # Verify SKILL.md exists
            skill_md = temp_dir / "SKILL.md"
            if not skill_md.exists():
                raise ValueError(f"Invalid skill: SKILL.md not found in {url}")

            # Parse skill info
            info = self._parse_skill_md(skill_md)

            # Move to target directory
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            target_dir = self.skills_dir / info.name

            if target_dir.exists():
                shutil.rmtree(target_dir)

            # Remove .git directory (version control not needed)
            git_dir = temp_dir / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir)

            shutil.move(str(temp_dir), str(target_dir))

            # Save installation metadata (including source URL)
            self._save_skill_meta(target_dir, source_url=url, source_type="github")

            # Update path info and metadata
            info.path = str(target_dir)
            info.source_url = url
            info.installed_at = datetime.now().isoformat()
            logger.info(f"Installed skill '{info.name}' from GitHub to {target_dir}")
            return info

        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to clone {url}: {e.stderr}")
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def remove_skill(self, skill_name: str) -> bool:
        """Remove a Skill"""
        if not self.skills_dir:
            return False

        skill_path = self.skills_dir / skill_name
        if skill_path.exists():
            shutil.rmtree(skill_path)
            logger.info(f"Removed skill '{skill_name}' from {skill_path}")
            return True

        # Also check disabled directory
        disabled_path = self.skills_dir / ".disabled" / skill_name
        if disabled_path.exists():
            shutil.rmtree(disabled_path)
            logger.info(f"Removed disabled skill '{skill_name}' from {disabled_path}")
            return True

        return False

    def disable_skill(self, skill_name: str) -> bool:
        """Disable a Skill"""
        if not self.skills_dir:
            return False

        skill_path = self.skills_dir / skill_name
        disabled_dir = self.skills_dir / ".disabled"

        if skill_path.exists():
            disabled_dir.mkdir(exist_ok=True)
            shutil.move(str(skill_path), str(disabled_dir / skill_name))
            logger.info(f"Disabled skill '{skill_name}'")
            return True

        return False

    def enable_skill(self, skill_name: str) -> bool:
        """Enable a Skill"""
        if not self.skills_dir:
            return False

        disabled_path = self.skills_dir / ".disabled" / skill_name

        if disabled_path.exists():
            shutil.move(str(disabled_path), str(self.skills_dir / skill_name))
            logger.info(f"Enabled skill '{skill_name}'")
            return True

        return False

    def get_skill(self, skill_name: str) -> Optional[SkillInfo]:
        """Get a Skill by name"""
        all_skills = self.list_skills(include_disabled=True)
        for skill in all_skills:
            if skill.name == skill_name:
                return skill
        return None
