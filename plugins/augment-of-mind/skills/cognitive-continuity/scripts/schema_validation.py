#!/usr/bin/env python3
"""Small standard-library JSON Schema validator for Continuity-owned schemas.

The package deliberately avoids a runtime dependency on ``jsonschema``.  This
module implements the draft-2020-12 vocabulary used by the bundled schemas and
fails closed when a schema asks for an unsupported keyword that affects data
shape.  It is not advertised as a general JSON Schema implementation.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_ASSERTIONS = {
    "$ref",
    "$schema",
    "$id",
    "$defs",
    "title",
    "description",
    "type",
    "const",
    "enum",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
    "format",
    "allOf",
    "anyOf",
    "oneOf",
    "if",
    "then",
    "else",
}


class SchemaError(RuntimeError):
    """Raised when a bundled schema cannot be loaded or interpreted safely."""


def _json_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    raise SchemaError(f"unsupported JSON Schema type: {expected}")


def _pointer(document: Any, fragment: str) -> Any:
    if fragment in ("", "#"):
        return document
    raw = fragment.removeprefix("#")
    if not raw.startswith("/"):
        raise SchemaError(f"unsupported JSON pointer fragment: {fragment}")
    current = document
    for part in raw[1:].split("/"):
        token = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise SchemaError(f"unresolved JSON pointer fragment: {fragment}")
        current = current[token]
    return current


class SchemaCatalog:
    """Load and validate instances against schemas rooted in one directory."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._documents: dict[Path, dict[str, Any]] = {}

    def load(self, name: str | Path) -> tuple[Path, dict[str, Any]]:
        path = (self.root / Path(name)).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise SchemaError(f"schema escapes catalog root: {name}") from exc
        if path not in self._documents:
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SchemaError(f"cannot load schema {path}: {exc}") from exc
            if not isinstance(value, dict):
                raise SchemaError(f"schema root is not an object: {path}")
            self._documents[path] = value
        return path, self._documents[path]

    def validate(self, instance: Any, schema_name: str | Path) -> list[str]:
        path, schema = self.load(schema_name)
        errors: list[str] = []
        self._validate(instance, schema, "$", path, schema, errors)
        return errors

    def _resolve_ref(
        self,
        ref: str,
        current_path: Path,
        current_document: dict[str, Any],
    ) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        if ref.startswith("#"):
            target = _pointer(current_document, ref)
            if not isinstance(target, dict):
                raise SchemaError(f"schema reference is not an object: {ref}")
            return current_path, current_document, target
        name, marker, fragment = ref.partition("#")
        path = (current_path.parent / name).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise SchemaError(f"schema reference escapes catalog root: {ref}") from exc
        loaded_path, document = self.load(path.relative_to(self.root))
        target = _pointer(document, f"#{fragment}" if marker else "#")
        if not isinstance(target, dict):
            raise SchemaError(f"schema reference is not an object: {ref}")
        return loaded_path, document, target

    def _validate(
        self,
        instance: Any,
        schema: dict[str, Any],
        location: str,
        schema_path: Path,
        schema_document: dict[str, Any],
        errors: list[str],
    ) -> None:
        unknown = set(schema) - SUPPORTED_ASSERTIONS
        if unknown:
            raise SchemaError(
                f"unsupported schema keyword(s) in {schema_path.name}: "
                + ", ".join(sorted(unknown))
            )

        if "$ref" in schema:
            target_path, target_document, target = self._resolve_ref(
                str(schema["$ref"]), schema_path, schema_document
            )
            self._validate(instance, target, location, target_path, target_document, errors)
            return

        if "const" in schema and instance != schema["const"]:
            errors.append(f"{location}: expected constant {schema['const']!r}")
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{location}: value is not in the allowed enum")

        expected = schema.get("type")
        if expected is not None:
            choices = [expected] if isinstance(expected, str) else list(expected)
            if not any(_json_type(instance, item) for item in choices):
                errors.append(f"{location}: expected type {' or '.join(choices)}")
                return

        for branch in schema.get("allOf", []):
            self._validate(instance, branch, location, schema_path, schema_document, errors)

        for keyword, required_matches in (("anyOf", 1), ("oneOf", 1)):
            if keyword not in schema:
                continue
            matches = 0
            branch_errors: list[list[str]] = []
            for branch in schema[keyword]:
                candidate: list[str] = []
                self._validate(instance, branch, location, schema_path, schema_document, candidate)
                branch_errors.append(candidate)
                if not candidate:
                    matches += 1
            valid = matches >= required_matches if keyword == "anyOf" else matches == required_matches
            if not valid:
                errors.append(f"{location}: failed {keyword} ({matches} matching branches)")

        if "if" in schema:
            condition_errors: list[str] = []
            self._validate(instance, schema["if"], location, schema_path, schema_document, condition_errors)
            branch = schema.get("then") if not condition_errors else schema.get("else")
            if branch is not None:
                self._validate(instance, branch, location, schema_path, schema_document, errors)

        if isinstance(instance, dict):
            required = schema.get("required", [])
            for key in required:
                if key not in instance:
                    errors.append(f"{location}: missing required property {key}")
            properties = schema.get("properties", {})
            for key, value in instance.items():
                child = f"{location}.{key}"
                if key in properties:
                    self._validate(value, properties[key], child, schema_path, schema_document, errors)
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{child}: additional property is not allowed")
                elif isinstance(schema.get("additionalProperties"), dict):
                    self._validate(
                        value,
                        schema["additionalProperties"],
                        child,
                        schema_path,
                        schema_document,
                        errors,
                    )

        if isinstance(instance, list):
            if len(instance) < int(schema.get("minItems", 0)):
                errors.append(f"{location}: too few items")
            if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
                errors.append(f"{location}: too many items")
            if schema.get("uniqueItems"):
                rendered = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in instance]
                if len(rendered) != len(set(rendered)):
                    errors.append(f"{location}: items are not unique")
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, value in enumerate(instance):
                    self._validate(
                        value,
                        item_schema,
                        f"{location}[{index}]",
                        schema_path,
                        schema_document,
                        errors,
                    )

        if isinstance(instance, str):
            if len(instance) < int(schema.get("minLength", 0)):
                errors.append(f"{location}: string is too short")
            if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
                errors.append(f"{location}: string is too long")
            if "pattern" in schema and re.fullmatch(str(schema["pattern"]), instance) is None:
                errors.append(f"{location}: string does not match required pattern")
            if schema.get("format") == "date-time":
                try:
                    parsed = datetime.fromisoformat(instance.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        raise ValueError("date-time lacks timezone")
                except ValueError:
                    errors.append(f"{location}: invalid RFC3339-compatible date-time")

        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if "minimum" in schema and instance < schema["minimum"]:
                errors.append(f"{location}: value is below minimum")
            if "maximum" in schema and instance > schema["maximum"]:
                errors.append(f"{location}: value is above maximum")
