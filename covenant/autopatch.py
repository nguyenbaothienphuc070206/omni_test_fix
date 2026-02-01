"""Phase 5: Self-healing smart contracts (v2.0) MVP.

Approach:
- Parse Python AST.
- Detect dangerous nodes/identifiers.
- Auto-patch by hard-blocking (raise) while keeping source runnable.

This is a safety gate, not a full rewriter.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import List, Tuple


_BANNED_NAMES = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "input",
    "globals",
    "locals",
}

_BANNED_ATTR_PREFIXES = ("__",)


@dataclass(slots=True)
class AuditIssue:
    kind: str
    detail: str
    line: int


class CovenantAuditor:
    def __init__(self) -> None:
        self._cache: dict[str, List[AuditIssue]] = {}
        self._cache_max = 1024

    def _key(self, source: str) -> str:
        return hashlib.blake2s(source.encode("utf-8"), digest_size=16).hexdigest()

    def _fast_flags(self, source: str) -> List[AuditIssue] | None:
        # Cheap substring checks (O(n) in bytes) before AST parse.
        s = source
        if "import " in s or "from " in s:
            return [AuditIssue(kind="import", detail="imports_not_allowed", line=1)]
        if "__builtins__" in s:
            return [AuditIssue(kind="builtins", detail="builtins_access_not_allowed", line=1)]
        for name in _BANNED_NAMES:
            if f"{name}(" in s:
                return [AuditIssue(kind="call", detail=f"banned_call:{name}", line=1)]
        return None

    def audit(self, source: str) -> List[AuditIssue]:
        k = self._key(source)
        cached = self._cache.get(k)
        if cached is not None:
            return cached

        fast = self._fast_flags(source)
        if fast is not None:
            issues = fast
        else:
            issues = self._audit_ast(source)

        if len(self._cache) >= self._cache_max:
            self._cache.clear()
        self._cache[k] = issues
        return issues

    def _audit_ast(self, source: str) -> List[AuditIssue]:
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return [AuditIssue(kind="syntax", detail=str(e), line=int(getattr(e, "lineno", 1) or 1))]

        issues: List[AuditIssue] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                issues.append(AuditIssue("import", "imports_not_allowed", getattr(node, "lineno", 1)))

            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id in _BANNED_NAMES:
                    issues.append(AuditIssue("call", f"banned_call:{fn.id}", getattr(node, "lineno", 1)))

            if isinstance(node, ast.Attribute) and isinstance(node.attr, str):
                if node.attr.startswith(_BANNED_ATTR_PREFIXES):
                    issues.append(AuditIssue("attr", f"private_attr:{node.attr}", getattr(node, "lineno", 1)))

        return issues

    def auto_patch(self, source: str) -> Tuple[str, List[AuditIssue]]:
        issues = self.audit(source)
        if not issues:
            return source, []

        # Simple patch: prepend a guard that blocks execution.
        header = "".join(
            [
                    "# AUTO-PATCHED: execution blocked by covenant policy\n",
                "def __contract_blocked__():\n",
                    "    raise RuntimeError('contract blocked by covenant policy')\n",
                "__contract_blocked__()\n\n",
            ]
        )
        return header + source, issues


covenant_auditor = CovenantAuditor()
