"""
DAG Resolver — Topological sort of services into parallel-safe launch tiers.
Each tier contains services that can be launched in parallel.
"""

from collections import defaultdict, deque


def resolve_tiers(services: dict = None) -> list:
    """
    Kahn's algorithm → list of tiers (each tier = set of service names).
    Services within a tier have no dependencies on each other → parallel-safe.
    """
    if services is None:
        from .config import SERVICES as services
    in_degree = {name: len(cfg.get("depends", [])) for name, cfg in services.items()}
    dependents = defaultdict(set)
    for name, cfg in services.items():
        for dep in cfg.get("depends", []):
            dependents[dep].add(name)

    queue = deque([n for n, d in in_degree.items() if d == 0])
    tiers = []
    while queue:
        tier = set()
        for _ in range(len(queue)):
            node = queue.popleft()
            tier.add(node)
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        tiers.append(tier)

    if sum(len(t) for t in tiers) != len(services):
        raise RuntimeError("Circular dependency detected in service configuration")
    return tiers
