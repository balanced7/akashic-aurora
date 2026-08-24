"""
Infrastructure Orchestration System (SYSTEM 1 - To Be Built)

Semantic Relationship: Infrastructure enables all other systems

Purpose: Ensure Redis, Docker, WSL are available and healthy.

Components (to build):
- orchestrator.py: launch_infrastructure_systems()
- wsl.py: check_wsl_available(), enable_wsl_if_needed()
- docker.py: start_docker_if_needed()
- redis.py: start_redis_with_health_check()
- health_check.py: check_infrastructure_health()

All functions return status dict so downstream systems know what's available.
Aggressive timeouts (5s max) - fail fast, continue gracefully.
"""

from .health_check import check_infrastructure_health

__all__ = ["check_infrastructure_health"]
