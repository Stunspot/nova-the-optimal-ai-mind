from __future__ import annotations

import hashlib
import html
import json
import os
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union


ALCHEMY_ADAPTER_ID = "alchemy-character-json/unversioned"
FOUNDRY_ADAPTER_ID = "foundry-v14-module/14.365"
LOSS_REPORT_FORMAT = "cd-ludis-loss-report/v1"
FOUNDRY_BUNDLE_FORMAT = "cd-ludis-foundry-v14/v1"
FOUNDRY_GENERATION = 14
FOUNDRY_BUILD = 365

AssetValue = Union[bytes, bytearray, memoryview, str, os.PathLike]
AssetMap = Mapping[str, AssetValue]

_ALCHEMY_NATIVE_FIELDS = (
    "appearance",
    "type",
    "typeTags",
    "race",
    "abilityScores",
    "currentHp",
    "maxHp",
    "armorClass",
    "movementModes",
    "textBlocks",
    "imageUri",
    "spells",
)
_ALCHEMY_ALIASES = {
    "type_tags": "typeTags",
    "current_hp": "currentHp",
    "max_hp": "maxHp",
    "armor_class": "armorClass",
    "movement_modes": "movementModes",
    "text_blocks": "textBlocks",
    "image_uri": "imageUri",
}
_ALCHEMY_KINDS = {"character", "npc", "creature"}
_TABLE_KINDS = {"table", "roll-table", "roll_table", "random-table", "random_table", "rumor-table", "rumor_table"}
_SCENE_KINDS = {"scene", "map", "battle-map", "battle_map", "region-map", "region_map"}
_SAFE_MODULE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SAFE_EXTENSION = re.compile(r"^\.[A-Za-z0-9]{1,10}$")


class AdapterError(ValueError):
    """A deterministic adapter could not safely represent its input."""


def _pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AdapterError("adapter input must be JSON-compatible") from exc
    return (rendered + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _slug(value: str, fallback: str = "item", limit: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._").lower()
    return (slug or fallback)[:limit]


def _source_id(obj: Mapping[str, Any], fallback: str) -> str:
    value = obj.get("id")
    return value if isinstance(value, str) and value.strip() else fallback


def _object_name(obj: Mapping[str, Any]) -> Optional[str]:
    data = obj.get("data") if isinstance(obj.get("data"), Mapping) else {}
    alchemy = data.get("alchemy") if isinstance(data.get("alchemy"), Mapping) else {}
    for value in (alchemy.get("name"), data.get("name"), obj.get("name"), obj.get("title")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _object_kind(obj: Mapping[str, Any]) -> str:
    value = obj.get("kind")
    return value.casefold().replace(" ", "-") if isinstance(value, str) else ""


def _object_data(obj: Mapping[str, Any]) -> Mapping[str, Any]:
    value = obj.get("data")
    return value if isinstance(value, Mapping) else {}


def _narrative(obj: Mapping[str, Any]) -> Optional[str]:
    data = _object_data(obj)
    alchemy = data.get("alchemy") if isinstance(data.get("alchemy"), Mapping) else {}
    for value in (
        alchemy.get("description"),
        data.get("description"),
        obj.get("content"),
        obj.get("text"),
        obj.get("summary"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _objects(projection: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    values = projection.get("objects", [])
    if not isinstance(values, list):
        raise AdapterError("projection.objects must be an array")
    if not all(isinstance(value, Mapping) for value in values):
        raise AdapterError("every projection object must be an object")
    return list(values)


def _asset_records(projection: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    values = projection.get("assets", [])
    if not isinstance(values, list):
        raise AdapterError("projection.assets must be an array")
    if not all(isinstance(value, Mapping) for value in values):
        raise AdapterError("every projection asset must be an object")
    return list(values)


def _safe_member_path(path: str) -> bool:
    if not isinstance(path, str) or not path or "\\" in path:
        return False
    rel = PurePosixPath(path)
    return not rel.is_absolute() and all(part not in {"", ".", ".."} for part in rel.parts)


def _loss(severity: str, source_id: str, code: str, message: str) -> Dict[str, str]:
    return {
        "severity": severity,
        "source_id": source_id,
        "code": code,
        "message": message,
    }


def _loss_report(
    adapter: str,
    target: str,
    items: Sequence[Mapping[str, Any]],
    emitted: Mapping[str, Any],
) -> Dict[str, Any]:
    blocked = sum(1 for item in items if item.get("severity") == "blocked")
    warnings = sum(1 for item in items if item.get("severity") == "warning")
    emitted_total = sum(value for value in emitted.values() if isinstance(value, int))
    if emitted_total == 0:
        status = "blocked"
    elif blocked or warnings:
        status = "statically_ready_with_losses"
    else:
        status = "statically_ready"
    compatibility_claim = {
        "blocked": "No target records were emitted; live target ingestion and rendering remain unverified.",
        "statically_ready_with_losses": (
            "Static structure checks passed for emitted records with documented losses; "
            "live target ingestion and rendering remain unverified."
        ),
        "statically_ready": "Static structure checks passed; live target ingestion and rendering remain unverified.",
    }[status]
    return {
        "format": LOSS_REPORT_FORMAT,
        "adapter": adapter,
        "target": target,
        "status": status,
        "compatibility": {
            "state": status,
            "live_import_verified": False,
            "claim": compatibility_claim,
        },
        "items": list(items),
        "summary": {
            "blocked": blocked,
            "warnings": warnings,
            "emitted": dict(emitted),
        },
    }


def _explicit_system_key(obj: Mapping[str, Any], campaign: Mapping[str, Any]) -> Optional[str]:
    data = _object_data(obj)
    alchemy = data.get("alchemy") if isinstance(data.get("alchemy"), Mapping) else {}
    campaign_data = campaign.get("data") if isinstance(campaign.get("data"), Mapping) else {}
    for value in (
        alchemy.get("systemKey"),
        data.get("systemKey"),
        obj.get("systemKey"),
        campaign.get("systemKey"),
        campaign_data.get("systemKey"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _text_block_entries(label: str, values: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(values, list):
        return None
    blocks: List[Dict[str, str]] = []
    for index, value in enumerate(values, start=1):
        if isinstance(value, str) and value.strip():
            blocks.append({"title": "{} {}".format(label[:-1] if label.endswith("s") else label, index), "body": value.strip()})
        elif isinstance(value, Mapping):
            title = value.get("title") or value.get("name")
            body = value.get("body") or value.get("description") or value.get("text")
            if isinstance(title, str) and title.strip() and isinstance(body, str) and body.strip():
                blocks.append({"title": title.strip(), "body": body.strip()})
    return {"title": label, "textBlocks": blocks} if blocks else None


def _alchemy_character(
    obj: Mapping[str, Any],
    campaign: Mapping[str, Any],
    fallback_id: str,
    loss_items: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    source_id = _source_id(obj, fallback_id)
    kind = _object_kind(obj)
    if kind not in _ALCHEMY_KINDS:
        loss_items.append(_loss("warning", source_id, "unsupported_object_kind", "Alchemy Character JSON does not represent object kind {!r}.".format(kind or "unknown")))
        return None
    name = _object_name(obj)
    if name is None:
        loss_items.append(_loss("blocked", source_id, "missing_character_name", "Character-like object has no explicit name or title."))
        return None
    system_key = _explicit_system_key(obj, campaign)
    if system_key is None:
        loss_items.append(_loss("blocked", source_id, "missing_system_key", "Alchemy export requires an explicit systemKey; campaign.system is not inferred."))
        return None

    data = _object_data(obj)
    native = data.get("alchemy") if isinstance(data.get("alchemy"), Mapping) else {}
    character: Dict[str, Any] = {"name": name, "systemKey": system_key}
    explicit_npc = native.get("isNPC") if "isNPC" in native else data.get("isNPC")
    if isinstance(explicit_npc, bool):
        character["isNPC"] = explicit_npc
    elif kind in {"npc", "creature"}:
        character["isNPC"] = True

    description = _narrative(obj)
    if description is not None:
        character["description"] = description

    consumed = {"alchemy", "name", "description", "systemKey", "isNPC"}
    for field in _ALCHEMY_NATIVE_FIELDS:
        if field in native:
            character[field] = native[field]
        elif field in data:
            character[field] = data[field]
        consumed.add(field)
    for source, target in _ALCHEMY_ALIASES.items():
        if target not in character and source in data:
            character[target] = data[source]
        consumed.add(source)

    ability_scores = data.get("ability_scores")
    if "abilityScores" not in character and isinstance(ability_scores, Mapping):
        character["abilityScores"] = [
            {"name": str(key), "value": value}
            for key, value in ability_scores.items()
        ]
    consumed.add("ability_scores")

    hp = data.get("hp")
    if isinstance(hp, Mapping):
        if "currentHp" not in character and "current" in hp:
            character["currentHp"] = hp["current"]
        if "maxHp" not in character and "max" in hp:
            character["maxHp"] = hp["max"]
        consumed.add("hp")

    text_blocks = character.get("textBlocks")
    if text_blocks is None:
        text_blocks = []

    if "actions" in native:
        character["actions"] = native["actions"]
        consumed.add("actions")
    elif "actions" in data:
        consumed.add("actions")
        action_values = data["actions"]
        native_action_shape = (
            isinstance(action_values, list)
            and bool(action_values)
            and all(
                isinstance(value, Mapping)
                and isinstance(value.get("name"), str)
                and isinstance(value.get("steps"), list)
                for value in action_values
            )
        )
        if native_action_shape:
            character["actions"] = action_values
        else:
            block = _text_block_entries("Actions", action_values)
            if block is not None and isinstance(text_blocks, list):
                text_blocks.append(block)

    if "traits" in data:
        consumed.add("traits")
        block = _text_block_entries("Traits", data["traits"])
        if block is not None and isinstance(text_blocks, list):
            text_blocks.append(block)
    if isinstance(text_blocks, list) and text_blocks:
        character["textBlocks"] = text_blocks

    substantive = [
        value
        for key, value in character.items()
        if key not in {"name", "systemKey", "isNPC"} and value not in (None, "", [], {})
    ]
    if not substantive:
        loss_items.append(_loss("blocked", source_id, "insufficient_character_data", "Named character has no explicit narrative or structured character data."))
        return None

    native_known = set(_ALCHEMY_NATIVE_FIELDS) | {"name", "description", "systemKey", "isNPC", "actions"}
    unrepresented = sorted(str(key) for key in data if key not in consumed and key != "alchemy")
    native_unrepresented = sorted(str(key) for key in native if key not in native_known)
    dropped = unrepresented + ["alchemy.{}".format(key) for key in native_unrepresented]
    if dropped:
        loss_items.append(
            _loss(
                "warning",
                source_id,
                "unrepresented_fields",
                "Not represented in the conservative Alchemy profile: " + ", ".join(dropped),
            )
        )
    return character


def _validate_alchemy_character(value: Any, label: str) -> List[str]:
    errors: List[str] = []
    if not isinstance(value, dict):
        return ["{} must contain a JSON object".format(label)]
    for field in ("name", "systemKey"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append("{}.{} must be a non-empty string".format(label, field))
    if "isNPC" in value and not isinstance(value["isNPC"], bool):
        errors.append("{}.isNPC must be boolean".format(label))
    for field in ("description", "appearance", "type", "race"):
        if field in value and not isinstance(value[field], str):
            errors.append("{}.{} must be a string".format(label, field))
    if "imageUri" in value and (not isinstance(value["imageUri"], str) or not value["imageUri"].strip()):
        errors.append("{}.imageUri must be a non-empty string".format(label))

    tags = value.get("typeTags")
    if tags is not None:
        if not isinstance(tags, list):
            errors.append("{}.typeTags must be an array".format(label))
        else:
            for index, tag in enumerate(tags):
                if not isinstance(tag, str):
                    errors.append("{}.typeTags[{}] must be a string".format(label, index))

    for field in ("currentHp", "maxHp", "armorClass"):
        if field in value and (isinstance(value[field], bool) or not isinstance(value[field], (int, float))):
            errors.append("{}.{} must be numeric".format(label, field))
    scores = value.get("abilityScores")
    if scores is not None:
        if not isinstance(scores, list):
            errors.append("{}.abilityScores must be an array".format(label))
        else:
            for index, score in enumerate(scores):
                if not isinstance(score, dict):
                    errors.append("{}.abilityScores[{}] must be an object".format(label, index))
                    continue
                if not isinstance(score.get("name"), str) or not score["name"].strip():
                    errors.append("{}.abilityScores[{}].name must be a non-empty string".format(label, index))
                if isinstance(score.get("value"), bool) or not isinstance(score.get("value"), (int, float)):
                    errors.append("{}.abilityScores[{}].value must be numeric".format(label, index))
    modes = value.get("movementModes")
    if modes is not None:
        if not isinstance(modes, list):
            errors.append("{}.movementModes must be an array".format(label))
        else:
            for index, mode in enumerate(modes):
                if not isinstance(mode, dict):
                    errors.append("{}.movementModes[{}] must be an object".format(label, index))
                    continue
                if not isinstance(mode.get("mode"), str) or not mode["mode"].strip():
                    errors.append("{}.movementModes[{}].mode must be a non-empty string".format(label, index))
                if isinstance(mode.get("distance"), bool) or not isinstance(mode.get("distance"), (int, float)):
                    errors.append("{}.movementModes[{}].distance must be numeric".format(label, index))

    blocks = value.get("textBlocks")
    if blocks is not None:
        if not isinstance(blocks, list):
            errors.append("{}.textBlocks must be an array".format(label))
        else:
            for section_index, section in enumerate(blocks):
                section_label = "{}.textBlocks[{}]".format(label, section_index)
                if not isinstance(section, dict):
                    errors.append("{} must be an object".format(section_label))
                    continue
                if not isinstance(section.get("title"), str) or not section["title"].strip():
                    errors.append("{}.title must be a non-empty string".format(section_label))
                entries = section.get("textBlocks")
                if not isinstance(entries, list):
                    errors.append("{}.textBlocks must be an array".format(section_label))
                    continue
                for block_index, block in enumerate(entries):
                    block_label = "{}.textBlocks[{}]".format(section_label, block_index)
                    if not isinstance(block, dict):
                        errors.append("{} must be an object".format(block_label))
                        continue
                    if not isinstance(block.get("title"), str) or not block["title"].strip():
                        errors.append("{}.title must be a non-empty string".format(block_label))
                    if not isinstance(block.get("body"), str):
                        errors.append("{}.body must be a string".format(block_label))

    actions = value.get("actions")
    if actions is not None:
        if not isinstance(actions, list):
            errors.append("{}.actions must be an array".format(label))
        else:
            for index, action in enumerate(actions):
                action_label = "{}.actions[{}]".format(label, index)
                if not isinstance(action, dict):
                    errors.append("{} must be an object".format(action_label))
                    continue
                if not isinstance(action.get("name"), str) or not action["name"].strip():
                    errors.append("{}.name must be a non-empty string".format(action_label))
                if "description" in action and not isinstance(action["description"], str):
                    errors.append("{}.description must be a string".format(action_label))
                if "sortOrder" in action and (isinstance(action["sortOrder"], bool) or not isinstance(action["sortOrder"], (int, float))):
                    errors.append("{}.sortOrder must be numeric".format(action_label))
                steps = action.get("steps")
                if not isinstance(steps, list):
                    errors.append("{}.steps must be an array".format(action_label))
                else:
                    for step_index, step in enumerate(steps):
                        step_label = "{}.steps[{}]".format(action_label, step_index)
                        if not isinstance(step, dict):
                            errors.append("{} must be an object".format(step_label))
                        elif not isinstance(step.get("type"), str) or not step["type"].strip():
                            errors.append("{}.type must be a non-empty string".format(step_label))

    spells = value.get("spells")
    if spells is not None:
        if not isinstance(spells, list):
            errors.append("{}.spells must be an array".format(label))
        else:
            for index, spell in enumerate(spells):
                spell_label = "{}.spells[{}]".format(label, index)
                if not isinstance(spell, dict):
                    errors.append("{} must be an object".format(spell_label))
                elif not isinstance(spell.get("name"), str) or not spell["name"].strip():
                    errors.append("{}.name must be a non-empty string".format(spell_label))
    return errors
def _decode_json(files: Mapping[str, bytes], path: str, errors: List[str]) -> Any:
    data = files.get(path)
    if not isinstance(data, bytes):
        errors.append("{} must be bytes".format(path))
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append("{} is not valid UTF-8 JSON: {}".format(path, exc))
        return None


def _alchemy_character_paths(characters: Sequence[Mapping[str, Any]]) -> List[str]:
    """Derive the only allowed individual paths from ordered bulk records."""
    used_names = set()
    paths: List[str] = []
    for character in characters:
        raw_name = character.get("name")
        name = raw_name if isinstance(raw_name, str) and raw_name.strip() else "character"
        base = _slug(name, "character")
        filename = "{}.json".format(base)
        suffix = 2
        while filename.casefold() in used_names:
            filename = "{}-{}.json".format(base, suffix)
            suffix += 1
        used_names.add(filename.casefold())
        paths.append(filename)
    return paths


def _validate_loss_report_compatibility(report: Mapping[str, Any], label: str, errors: List[str]) -> Optional[str]:
    status = report.get("status")
    allowed = {"blocked", "statically_ready_with_losses", "statically_ready"}
    if status not in allowed:
        errors.append("{} status is invalid".format(label))
        return None
    compatibility = report.get("compatibility")
    if not isinstance(compatibility, dict):
        errors.append("{} compatibility must be an object".format(label))
    else:
        if compatibility.get("live_import_verified") is not False:
            errors.append("{} must label live import unverified".format(label))
        if compatibility.get("state") != status:
            errors.append("{} compatibility.state must exactly match status".format(label))
    return status


def validate_alchemy_character_files(files: Mapping[str, bytes]) -> List[str]:
    errors: List[str] = []
    actual_paths = set(files)
    for path, data in files.items():
        if not _safe_member_path(path):
            errors.append("unsafe output path: {}".format(path))
        if not isinstance(data, bytes):
            errors.append("{} must be bytes".format(path))

    report_path = "reports/loss-report.json"
    report = _decode_json(files, report_path, errors)
    status: Optional[str] = None
    declared_count: Any = None
    declared_paths: Any = None
    if isinstance(report, dict):
        if report.get("format") != LOSS_REPORT_FORMAT:
            errors.append("loss report has unsupported format")
        if report.get("adapter") != ALCHEMY_ADAPTER_ID:
            errors.append("loss report adapter does not match Alchemy")
        status = _validate_loss_report_compatibility(report, "Alchemy loss report", errors)
        summary = report.get("summary")
        emitted = summary.get("emitted") if isinstance(summary, dict) else None
        if not isinstance(emitted, dict):
            errors.append("Alchemy loss report summary.emitted must be an object")
        else:
            declared_count = emitted.get("characters")
            declared_paths = emitted.get("character_files")
            if not isinstance(declared_count, int) or isinstance(declared_count, bool) or declared_count < 0:
                errors.append("Alchemy loss report emitted.characters must be a non-negative integer")
            if (
                not isinstance(declared_paths, list)
                or not all(isinstance(path, str) for path in declared_paths)
                or len(set(declared_paths)) != len(declared_paths)
            ):
                errors.append("Alchemy loss report emitted.character_files must be a unique string array")
                declared_paths = None

    if status == "blocked":
        expected_members = {report_path}
        unexpected = sorted(path for path in actual_paths - expected_members if isinstance(path, str))
        missing = sorted(expected_members - actual_paths)
        if unexpected or missing:
            errors.append(
                "blocked Alchemy output members do not match the exact allowlist; unexpected={} missing={}".format(
                    unexpected, missing
                )
            )
        if declared_count != 0 or declared_paths != []:
            errors.append("blocked Alchemy output must declare zero characters and no character files")
        return errors

    bulk_path = "_all.json"
    bulk = _decode_json(files, bulk_path, errors)
    characters: Optional[List[Mapping[str, Any]]] = None
    expected_paths: List[str] = []
    if not isinstance(bulk, dict) or set(bulk) != {"characters"} or not isinstance(bulk.get("characters"), list):
        errors.append("_all.json must be an object containing only a characters array")
    else:
        raw_characters = bulk["characters"]
        errors.extend(
            error
            for index, value in enumerate(raw_characters)
            for error in _validate_alchemy_character(value, "_all.json.characters[{}]".format(index))
        )
        if all(isinstance(value, Mapping) for value in raw_characters):
            characters = list(raw_characters)
            expected_paths = _alchemy_character_paths(characters)

    expected_members = {report_path, bulk_path, *expected_paths}
    unexpected = sorted(path for path in actual_paths - expected_members if isinstance(path, str))
    missing = sorted(expected_members - actual_paths)
    if unexpected or missing:
        errors.append(
            "Alchemy output members do not match the exact allowlist; unexpected={} missing={}".format(
                unexpected, missing
            )
        )
    if not expected_paths:
        errors.append("at least one individual Alchemy character JSON file is required")
    if declared_count != len(expected_paths):
        errors.append("Alchemy loss report emitted.characters does not match exact character count")
    if declared_paths != expected_paths:
        errors.append("Alchemy loss report emitted.character_files does not match deterministic paths")

    individuals: List[Any] = []
    for path in expected_paths:
        value = _decode_json(files, path, errors)
        individuals.append(value)
        errors.extend(_validate_alchemy_character(value, path))
    if characters is not None and individuals != characters:
        errors.append("_all.json characters do not exactly match their deterministic individual files")
    return errors


def render_alchemy_character_json(
    projection: Mapping[str, Any],
    assets: Optional[AssetMap] = None,
) -> Dict[str, bytes]:
    del assets
    campaign_value = projection.get("campaign", {})
    campaign = campaign_value if isinstance(campaign_value, Mapping) else {}
    loss_items: List[Dict[str, str]] = []
    rendered: List[Tuple[str, str, Dict[str, Any]]] = []
    for index, obj in enumerate(sorted(_objects(projection), key=lambda item: str(item.get("id") or item.get("title") or "")), start=1):
        character = _alchemy_character(obj, campaign, "character-{}".format(index), loss_items)
        if character is None:
            continue
        source_id = _source_id(obj, "character-{}".format(index))
        rendered.append((source_id, character["name"], character))
        if obj.get("asset_ids"):
            loss_items.append(
                _loss(
                    "warning",
                    source_id,
                    "local_assets_not_embedded",
                    "Alchemy documents imageUri, not local sidecar embedding; referenced assets were omitted unless an explicit imageUri was supplied.",
                )
            )
    for index, record in enumerate(_asset_records(projection), start=1):
        asset_id = record.get("id")
        loss_items.append(
            _loss(
                "warning",
                asset_id if isinstance(asset_id, str) and asset_id else "asset-{}".format(index),
                "asset_not_exported",
                "Alchemy Character JSON has no documented local sidecar-asset import contract.",
            )
        )

    files: Dict[str, bytes] = {}
    characters = [character for _source_id_value, _name, character in rendered]
    character_paths = _alchemy_character_paths(characters)
    for filename, character in zip(character_paths, characters):
        files[filename] = _pretty_json_bytes(character)
    if characters:
        files["_all.json"] = _pretty_json_bytes({"characters": characters})

    report = _loss_report(
        ALCHEMY_ADAPTER_ID,
        "Alchemy Character JSON, unversioned official format",
        loss_items,
        {"characters": len(characters), "character_files": character_paths},
    )
    files["reports/loss-report.json"] = _pretty_json_bytes(report)
    validation_errors = validate_alchemy_character_files(files)
    if validation_errors:
        raise AdapterError("invalid Alchemy adapter output: " + "; ".join(validation_errors))
    return files


def _coerce_asset_bytes(value: AssetValue, asset_id: str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, (str, os.PathLike)):
        path = Path(value)
        if not path.is_file():
            raise AdapterError("asset mapping for {} is not a file: {}".format(asset_id, path))
        return path.read_bytes()
    raise AdapterError("asset mapping for {} must be bytes or a filesystem path".format(asset_id))


def _asset_value(asset_map: AssetMap, record: Mapping[str, Any]) -> Optional[AssetValue]:
    asset_id = record.get("id")
    source_path = record.get("path")
    if isinstance(asset_id, str) and asset_id in asset_map:
        return asset_map[asset_id]
    if isinstance(source_path, str) and source_path in asset_map:
        return asset_map[source_path]
    return None


def _foundry_module_id(projection: Mapping[str, Any], requested: Optional[str]) -> str:
    if requested is not None:
        module_id = requested.strip()
    else:
        campaign = projection.get("campaign")
        campaign = campaign if isinstance(campaign, Mapping) else {}
        seed = campaign.get("id") or campaign.get("title") or "campaign"
        module_id = "ludis-" + _slug(str(seed), "campaign", 60).replace("_", "-").replace(".", "-")
    if not _SAFE_MODULE_ID.fullmatch(module_id):
        raise AdapterError("Foundry module id must match ^[a-z0-9][a-z0-9-]*$")
    return module_id


def _foundry_title(projection: Mapping[str, Any], requested: Optional[str]) -> str:
    if isinstance(requested, str) and requested.strip():
        return requested.strip()
    campaign = projection.get("campaign")
    campaign = campaign if isinstance(campaign, Mapping) else {}
    title = campaign.get("title")
    return "Ludis: {}".format(title.strip()) if isinstance(title, str) and title.strip() else "Ludis Campaign Bundle"


def _foundry_markdown(obj: Mapping[str, Any], name: str) -> str:
    kind = _object_kind(obj) or "campaign-object"
    narrative = _narrative(obj)
    if narrative is None:
        data = _object_data(obj)
        if data:
            narrative = "Structured source data:\n\n" + json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)
        else:
            narrative = "_No additional source content was supplied._"
    return "# {}\n\nType: {}\n\n{}\n".format(name, kind, narrative.rstrip())


def _foundry_flags(source_id: str) -> Dict[str, Any]:
    return {"ludis": {"sourceId": source_id}}


def _foundry_revision_input(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned = {str(key): _foundry_revision_input(item) for key, item in value.items()}
        flags = cleaned.get("flags")
        if isinstance(flags, dict):
            ludis = flags.get("ludis")
            if isinstance(ludis, dict):
                ludis.pop("importRevisionSha256", None)
        return cleaned
    if isinstance(value, list):
        return [_foundry_revision_input(item) for item in value]
    return value


def _foundry_record_revision(record: Mapping[str, Any]) -> str:
    return _sha256(_canonical_json_bytes(_foundry_revision_input(record)))


def _stamp_foundry_identity(value: Any, campaign_id: str, audience: str) -> None:
    if isinstance(value, dict):
        flags = value.get("flags")
        ludis = flags.get("ludis") if isinstance(flags, dict) else None
        if isinstance(ludis, dict) and isinstance(ludis.get("sourceId"), str) and ludis["sourceId"]:
            ludis["campaignId"] = campaign_id
            ludis["audience"] = audience
            ludis.pop("importRevisionSha256", None)
        for item in value.values():
            _stamp_foundry_identity(item, campaign_id, audience)
    elif isinstance(value, list):
        for item in value:
            _stamp_foundry_identity(item, campaign_id, audience)


def _stamp_foundry_revision(record: Mapping[str, Any], flag_owner: Optional[Dict[str, Any]] = None) -> None:
    owner = flag_owner if flag_owner is not None else record
    flags = owner.get("flags") if isinstance(owner, dict) else None
    ludis = flags.get("ludis") if isinstance(flags, dict) else None
    if not isinstance(ludis, dict):
        raise AdapterError("Foundry import record lacks flags.ludis revision owner")
    ludis["importRevisionSha256"] = _foundry_record_revision(record)


def _journal_document(obj: Mapping[str, Any], source_id: str, name: str) -> Dict[str, Any]:
    page_id = source_id + ":page:1"
    return {
        "name": name,
        "ownership": {"default": 0},
        "flags": _foundry_flags(source_id),
        "pages": [
            {
                "name": name,
                "type": "text",
                "sort": 0,
                "text": {"format": 2, "markdown": _foundry_markdown(obj, name)},
                "flags": _foundry_flags(page_id),
            }
        ],
    }


def _positive_int(value: Any) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _roll_table_document(
    obj: Mapping[str, Any],
    source_id: str,
    name: str,
    loss_items: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    data = _object_data(obj)
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        loss_items.append(_loss("warning", source_id, "roll_table_demoted", "No explicit table entries were supplied; content was preserved as a JournalEntry."))
        return None
    normalized: List[Tuple[str, int]] = []
    for index, entry in enumerate(entries, start=1):
        if isinstance(entry, str):
            text = entry.strip()
            weight = 1
        elif isinstance(entry, Mapping):
            raw_text = entry.get("text") if "text" in entry else entry.get("result")
            text = raw_text.strip() if isinstance(raw_text, str) else ""
            weight = entry.get("weight", 1)
        else:
            text = ""
            weight = 1
        if not text:
            loss_items.append(_loss("warning", source_id, "table_entry_omitted", "Table entry {} has no explicit text.".format(index)))
            continue
        if _positive_int(weight) is None:
            loss_items.append(_loss("warning", source_id, "table_entry_omitted", "Table entry {} has a non-positive or non-integer weight.".format(index)))
            continue
        normalized.append((text, weight))
    if not normalized:
        loss_items.append(_loss("warning", source_id, "roll_table_demoted", "No usable explicit table entries remained; content was preserved as a JournalEntry."))
        return None
    cursor = 1
    results: List[Dict[str, Any]] = []
    for text, weight in normalized:
        results.append({
            "type": "text",
            "text": text,
            "weight": weight,
            "range": [cursor, cursor + weight - 1],
            "drawn": False,
        })
        cursor += weight
    document: Dict[str, Any] = {
        "name": name,
        "formula": "1d{}".format(cursor - 1),
        "ownership": {"default": 0},
        "flags": _foundry_flags(source_id),
        "results": results,
    }
    narrative = _narrative(obj)
    if narrative is not None:
        document["description"] = "<p>" + html.escape(narrative).replace("\n", "<br>") + "</p>"
    for field in ("replacement", "displayRoll"):
        if isinstance(data.get(field), bool):
            document[field] = data[field]
    return document


def _grid_data(value: Any, source_id: str, loss_items: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    if not isinstance(value, Mapping):
        return None
    output: Dict[str, Any] = {}
    grid_type = value.get("type")
    if isinstance(grid_type, int) and not isinstance(grid_type, bool) and grid_type >= 0:
        output["type"] = grid_type
    elif isinstance(grid_type, str):
        mapped = {"gridless": 0, "square": 1}.get(grid_type.casefold())
        if mapped is None:
            loss_items.append(_loss("warning", source_id, "grid_type_omitted", "Grid type {!r} is not in the conservative gridless/square mapping.".format(grid_type)))
        else:
            output["type"] = mapped
    for field in ("size", "distance"):
        field_value = value.get(field)
        if isinstance(field_value, (int, float)) and not isinstance(field_value, bool) and field_value > 0:
            output[field] = field_value
        elif field in value:
            loss_items.append(_loss("warning", source_id, "grid_field_omitted", "Grid {} must be a positive number.".format(field)))
    if isinstance(value.get("units"), str) and value["units"].strip():
        output["units"] = value["units"].strip()
    return output or None


def _background_asset_id(level: Mapping[str, Any]) -> Optional[str]:
    for key in ("background_asset_id", "asset_id"):
        value = level.get(key)
        if isinstance(value, str) and value:
            return value
    background = level.get("background")
    if isinstance(background, Mapping):
        for key in ("asset_id", "source_id"):
            value = background.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _scene_document(
    obj: Mapping[str, Any],
    source_id: str,
    name: str,
    module_id: str,
    module_assets: Mapping[str, str],
    loss_items: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    data = _object_data(obj)
    width = _positive_int(data.get("width"))
    height = _positive_int(data.get("height"))
    if width is None or height is None:
        loss_items.append(_loss("warning", source_id, "scene_demoted", "Scene width and height were not explicit positive integers; content was preserved as a JournalEntry."))
        return None

    raw_levels = data.get("levels")
    level_specs: List[Mapping[str, Any]]
    if isinstance(raw_levels, list) and raw_levels and all(isinstance(value, Mapping) for value in raw_levels):
        level_specs = list(raw_levels)
    else:
        background_id = data.get("background_asset_id")
        if not isinstance(background_id, str):
            background = data.get("background")
            background_id = _background_asset_id(background) if isinstance(background, Mapping) else None
        asset_ids = [value for value in obj.get("asset_ids", []) if isinstance(value, str)] if isinstance(obj.get("asset_ids"), list) else []
        if not isinstance(background_id, str) and len(asset_ids) == 1:
            background_id = asset_ids[0]
        level_specs = [{"name": name, "background_asset_id": background_id}] if isinstance(background_id, str) else []

    levels: List[Dict[str, Any]] = []
    for index, level_spec in enumerate(level_specs, start=1):
        asset_id = _background_asset_id(level_spec)
        if asset_id is None or asset_id not in module_assets:
            loss_items.append(_loss("warning", source_id, "scene_level_omitted", "Level {} has no resolved local background asset.".format(index)))
            continue
        level_source = level_spec.get("source_id") or level_spec.get("id") or "{}:level:{}".format(source_id, index)
        level_name = level_spec.get("name")
        if not isinstance(level_name, str) or not level_name.strip():
            level_name = name if len(level_specs) == 1 else "{} {}".format(name, index)
        level: Dict[str, Any] = {
            "name": level_name,
            "background": {"src": "modules/{}/{}".format(module_id, module_assets[asset_id])},
            "flags": _foundry_flags(str(level_source)),
        }
        elevation = level_spec.get("elevation")
        if isinstance(elevation, Mapping):
            clean_elevation = {
                key: value
                for key, value in elevation.items()
                if key in {"bottom", "top"} and isinstance(value, (int, float)) and not isinstance(value, bool)
            }
            if clean_elevation:
                level["elevation"] = clean_elevation
        levels.append(level)
    if not levels:
        loss_items.append(_loss("warning", source_id, "scene_demoted", "No scene level had a resolved local background; content was preserved as a JournalEntry."))
        return None

    scene: Dict[str, Any] = {
        "name": name,
        "width": width,
        "height": height,
        "ownership": {"default": 0},
        "flags": _foundry_flags(source_id),
    }
    padding = data.get("padding")
    if isinstance(padding, (int, float)) and not isinstance(padding, bool) and padding >= 0:
        scene["padding"] = padding
    grid = _grid_data(data.get("grid"), source_id, loss_items)
    if grid is not None:
        scene["grid"] = grid
    return {
        "sourceId": source_id,
        "scene": scene,
        "levels": levels,
        "initialLevelSourceId": levels[0]["flags"]["ludis"]["sourceId"],
    }


FOUNDRY_IMPORTER_TEMPLATE = r'''const MODULE_ID = "__LUDIS_MODULE_ID__";
const FLAG_SCOPE = "ludis";
const FLAG_KEY = "sourceId";
const DATA_PATH = "data/ludis-foundry-v14.json";
const SHA256_PATTERN = /^[0-9a-f]{64}$/;

function sourceId(document) {
  return document?.getFlag?.(FLAG_SCOPE, FLAG_KEY) ?? null;
}

function recordMetadata(record) {
  return record?.flags?.ludis ?? null;
}

function documentMetadata(document) {
  return {
    sourceId: sourceId(document),
    campaignId: document?.getFlag?.(FLAG_SCOPE, "campaignId") ?? null,
    audience: document?.getFlag?.(FLAG_SCOPE, "audience") ?? null,
    importRevisionSha256: document?.getFlag?.(FLAG_SCOPE, "importRevisionSha256") ?? null
  };
}

export function ludisIdentity(metadata) {
  const campaignId = metadata?.campaignId;
  const recordSourceId = metadata?.sourceId;
  if (typeof campaignId !== "string" || !campaignId || typeof recordSourceId !== "string" || !recordSourceId) {
    return null;
  }
  return JSON.stringify([campaignId, recordSourceId]);
}

export function classifyLudisImport(existingMetadata, incomingMetadata, existingType = null, incomingType = null) {
  const incomingIdentity = ludisIdentity(incomingMetadata);
  if (!incomingIdentity) return "invalid";
  if (!existingMetadata || ludisIdentity(existingMetadata) !== incomingIdentity) return "create";
  if (existingType && incomingType && existingType !== incomingType) return "conflict";
  if (
    existingMetadata.audience === incomingMetadata.audience &&
    existingMetadata.importRevisionSha256 === incomingMetadata.importRevisionSha256
  ) {
    return "skip";
  }
  return "conflict";
}

export function classifyLudisEmbeddedImport(existingEntry, incomingMetadata, incomingParentIdentity, incomingType) {
  const disposition = classifyLudisImport(existingEntry?.metadata, incomingMetadata, existingEntry?.type, incomingType);
  if (disposition === "skip" && existingEntry?.parentIdentity !== incomingParentIdentity) return "conflict";
  return disposition;
}

export function classifyLudisLevelImport(existingEntry, incomingMetadata, incomingParentIdentity) {
  return classifyLudisEmbeddedImport(existingEntry, incomingMetadata, incomingParentIdentity, "Level");
}

function incomingMetadataError(metadata, payload) {
  if (!ludisIdentity(metadata)) return "record lacks flags.ludis campaignId/sourceId identity";
  if (metadata.campaignId !== payload?.pack?.id) return "record campaignId does not match payload pack.id";
  if (metadata.audience !== payload?.audience) return "record audience does not match payload audience";
  if (typeof metadata.importRevisionSha256 !== "string" || !SHA256_PATTERN.test(metadata.importRevisionSha256)) {
    return "record lacks a valid flags.ludis.importRevisionSha256";
  }
  return null;
}

function addToIdentityIndex(index, collection, type, report, parentIdentity = null) {
  for (const document of collection ?? []) {
    const metadata = documentMetadata(document);
    const identity = ludisIdentity(metadata);
    if (!identity) continue;
    if (index.has(identity)) {
      report.errors.push(type + ": world contains duplicate Ludis identity " + identity);
      continue;
    }
    index.set(identity, {document, metadata, type, parentIdentity});
  }
}

function indexWorld(report) {
  const index = new Map();
  addToIdentityIndex(index, game.journal, "JournalEntry", report);
  addToIdentityIndex(index, game.tables, "RollTable", report);
  addToIdentityIndex(index, game.scenes, "Scene", report);
  for (const journal of game.journal ?? []) {
    const parentIdentity = ludisIdentity(documentMetadata(journal));
    addToIdentityIndex(index, journal.pages, "JournalEntryPage", report, parentIdentity);
  }
  for (const scene of game.scenes ?? []) {
    const parentIdentity = ludisIdentity(documentMetadata(scene));
    addToIdentityIndex(index, scene.levels, "Level", report, parentIdentity);
  }
  return index;
}

function recordConflict(report, type, incoming, existing, details = {}) {
  report.conflicts.push({
    type,
    campaignId: incoming.campaignId,
    sourceId: incoming.sourceId,
    incomingAudience: incoming.audience,
    existingAudience: existing.audience,
    incomingRevisionSha256: incoming.importRevisionSha256,
    existingRevisionSha256: existing.importRevisionSha256,
    ...details
  });
}

async function loadPayload() {
  const response = await fetch("modules/" + MODULE_ID + "/" + DATA_PATH);
  if (!response.ok) throw new Error("Could not load Ludis payload: HTTP " + response.status);
  const payload = await response.json();
  if (payload?.format !== "cd-ludis-foundry-v14/v1") throw new Error("Unsupported Ludis Foundry payload");
  if (game.release?.generation !== 14) {
    throw new Error("This bundle targets Foundry generation 14, not " + (game.release?.generation ?? "unknown"));
  }
  return payload;
}

async function importTopLevel(type, records, payload, report, existing) {
  for (const record of records) {
    const incoming = recordMetadata(record);
    const metadataError = incomingMetadataError(incoming, payload);
    if (metadataError) {
      report.errors.push(type + ": " + metadataError);
      continue;
    }
    const identity = ludisIdentity(incoming);
    const found = existing.get(identity);
    const disposition = classifyLudisImport(found?.metadata, incoming, found?.type, type);
    if (disposition === "conflict") {
      recordConflict(report, type, incoming, found.metadata, {reason: "content_or_type_mismatch"});
      continue;
    }

    let embeddedConflict = false;
    if (type === "JournalEntry") {
      if (!Array.isArray(record.pages) || !record.pages.length) {
        report.errors.push("JournalEntry " + incoming.sourceId + ": at least one JournalEntryPage is required");
        continue;
      }
      for (const pageData of record.pages) {
        const pageMetadata = recordMetadata(pageData);
        const pageError = incomingMetadataError(pageMetadata, payload);
        if (pageError) {
          report.errors.push("JournalEntry " + incoming.sourceId + ", Page: " + pageError);
          embeddedConflict = true;
          continue;
        }
        const pageIdentity = ludisIdentity(pageMetadata);
        const existingPage = existing.get(pageIdentity);
        const pageDisposition = classifyLudisEmbeddedImport(
          existingPage,
          pageMetadata,
          identity,
          "JournalEntryPage"
        );
        const expectedDisposition = disposition === "skip" ? "skip" : "create";
        if (pageDisposition !== expectedDisposition) {
          const parentMismatch =
            pageDisposition === "conflict" &&
            classifyLudisImport(existingPage?.metadata, pageMetadata, existingPage?.type, "JournalEntryPage") === "skip" &&
            existingPage?.parentIdentity !== identity;
          if (existingPage?.metadata) {
            recordConflict(report, "JournalEntryPage", pageMetadata, existingPage.metadata, {
              reason: parentMismatch ? "parent_document_mismatch" : "content_or_type_mismatch",
              incomingParentIdentity: identity,
              existingParentIdentity: existingPage?.parentIdentity ?? null
            });
          } else {
            report.conflicts.push({
              type: "JournalEntryPage",
              campaignId: pageMetadata.campaignId,
              sourceId: pageMetadata.sourceId,
              reason: "missing_embedded_document",
              incomingParentIdentity: identity,
              existingParentIdentity: null
            });
          }
          embeddedConflict = true;
        }
      }
    }
    if (embeddedConflict) continue;
    if (disposition === "skip") {
      report.skipped[type] += 1;
      continue;
    }
    try {
      const [created] = await CONFIG[type].documentClass.createDocuments([record]);
      existing.set(identity, {document: created, metadata: incoming, type, parentIdentity: null});
      report.created[type] += 1;
    } catch (error) {
      report.errors.push(type + " " + incoming.sourceId + ": " + (error.message ?? error));
    }
  }
}

async function importScenes(records, payload, report, existing) {
  for (const record of records) {
    const incoming = recordMetadata(record?.scene);
    const id = record?.sourceId;
    const metadataError = incomingMetadataError(incoming, payload);
    if (!id || incoming?.sourceId !== id || metadataError) {
      report.errors.push("Scene: " + (metadataError ?? "record lacks a consistent flags.ludis.sourceId"));
      continue;
    }
    const identity = ludisIdentity(incoming);
    const found = existing.get(identity);
    const disposition = classifyLudisImport(found?.metadata, incoming, found?.type, "Scene");
    if (disposition === "conflict") {
      recordConflict(report, "Scene", incoming, found.metadata, {reason: "content_or_type_mismatch"});
      continue;
    }

    const incomingLevels = new Map();
    const levelPlans = [];
    let preflightFailed = false;
    for (const levelData of record.levels ?? []) {
      const levelMetadata = recordMetadata(levelData);
      const levelError = incomingMetadataError(levelMetadata, payload);
      if (levelError) {
        report.errors.push("Scene " + id + ", Level: " + levelError);
        preflightFailed = true;
        continue;
      }
      const levelIdentity = ludisIdentity(levelMetadata);
      incomingLevels.set(levelMetadata.sourceId, levelMetadata);
      const existingLevel = existing.get(levelIdentity);
      const baseDisposition = classifyLudisImport(existingLevel?.metadata, levelMetadata, existingLevel?.type, "Level");
      const levelDisposition = classifyLudisLevelImport(existingLevel, levelMetadata, identity);
      if (levelDisposition === "conflict") {
        const parentMismatch = baseDisposition === "skip" && existingLevel?.parentIdentity !== identity;
        recordConflict(report, "Level", levelMetadata, existingLevel.metadata, {
          reason: parentMismatch ? "parent_scene_mismatch" : "content_or_type_mismatch",
          incomingParentIdentity: identity,
          existingParentIdentity: existingLevel?.parentIdentity ?? null
        });
        preflightFailed = true;
        continue;
      }
      levelPlans.push({levelData, levelMetadata, levelIdentity, levelDisposition});
    }
    if (!Array.isArray(record.levels) || !record.levels.length) {
      report.errors.push("Scene " + id + ": at least one Level is required");
      preflightFailed = true;
    }
    if (!incomingLevels.has(record.initialLevelSourceId)) {
      report.errors.push("Scene " + id + ": initialLevelSourceId does not name an incoming Level");
      preflightFailed = true;
    }
    if (preflightFailed) continue;

    let scene = found?.document ?? null;
    if (!scene) {
      try {
        [scene] = await CONFIG.Scene.documentClass.createDocuments([record.scene]);
        existing.set(identity, {document: scene, metadata: incoming, type: "Scene", parentIdentity: null});
        report.created.Scene += 1;
      } catch (error) {
        report.errors.push("Scene " + id + ": " + (error.message ?? error));
        continue;
      }
    } else {
      report.skipped.Scene += 1;
    }

    for (const plan of levelPlans) {
      if (plan.levelDisposition === "skip") {
        report.skipped.Level += 1;
        continue;
      }
      try {
        const [level] = await scene.createEmbeddedDocuments("Level", [plan.levelData]);
        existing.set(plan.levelIdentity, {
          document: level,
          metadata: plan.levelMetadata,
          type: "Level",
          parentIdentity: identity
        });
        report.created.Level += 1;
      } catch (error) {
        report.errors.push("Scene " + id + ", Level " + plan.levelMetadata.sourceId + ": " + (error.message ?? error));
      }
    }

    const initialMetadata = incomingLevels.get(record.initialLevelSourceId);
    const initialEntry = initialMetadata ? existing.get(ludisIdentity(initialMetadata)) : null;
    const initialLevel = initialEntry?.parentIdentity === identity ? initialEntry.document : null;
    if (!initialLevel) {
      report.errors.push("Scene " + id + ": initial Level was not created or matched under this Scene");
      continue;
    }
    if (scene.initialLevel?.id !== initialLevel.id) {
      try {
        await scene.update({initialLevel: initialLevel.id});
      } catch (error) {
        report.errors.push("Scene " + id + ", initial Level: " + (error.message ?? error));
      }
    }
  }
}

export async function importBundle() {
  if (!game.user?.isGM) throw new Error("Only a GM may import this Ludis bundle");
  const payload = await loadPayload();
  const report = {
    created: {JournalEntry: 0, RollTable: 0, Scene: 0, Level: 0},
    skipped: {JournalEntry: 0, RollTable: 0, Scene: 0, Level: 0},
    conflicts: [],
    errors: []
  };
  const existing = indexWorld(report);
  await importTopLevel("JournalEntry", payload.documents.JournalEntry, payload, report, existing);
  await importTopLevel("RollTable", payload.documents.RollTable, payload, report, existing);
  await importScenes(payload.documents.Scene, payload, report, existing);

  const created = Object.values(report.created).reduce((total, value) => total + value, 0);
  const skipped = Object.values(report.skipped).reduce((total, value) => total + value, 0);
  const message = "Ludis import finished: " + created + " created, " + skipped + " exact matches skipped, " + report.conflicts.length + " conflicts, " + report.errors.length + " errors.";
  if (report.errors.length || report.conflicts.length) {
    console.error("[" + MODULE_ID + "]", report);
    ui.notifications.error(message + " Conflicts were left unchanged.");
  } else {
    console.info("[" + MODULE_ID + "]", report);
    ui.notifications.info(message);
  }
  return report;
}

Hooks.once("ready", async () => {
  if (!game.user?.isGM) return;
  const module = game.modules.get(MODULE_ID);
  if (module) module.api = Object.freeze({importBundle});
  const dialogs = foundry?.applications?.api?.DialogV2;
  if (!dialogs) {
    ui.notifications.info("Ludis bundle ready. Run game.modules.get(" + JSON.stringify(MODULE_ID) + ").api.importBundle() to import it.");
    return;
  }
  const confirmed = await dialogs.confirm({
    window: {title: "Import Ludis campaign bundle"},
    content: "<p>Create or resume this campaign import? Exact matches are skipped. Changed content or audience for the same campaign object is reported as a conflict and left untouched.</p>",
    yes: {label: "Import or resume"},
    no: {label: "Not now"},
    modal: true
  });
  if (confirmed) await importBundle();
});
'''


def _asset_output_path(record: Mapping[str, Any], used: set) -> str:
    asset_id = str(record.get("id") or "asset")
    source_name = PurePosixPath(str(record.get("path") or asset_id)).name
    extension = PurePosixPath(source_name).suffix
    safe_extension = extension.lower() if _SAFE_EXTENSION.fullmatch(extension) else ""
    stem = source_name[:-len(extension)] if extension else source_name
    base = "{}-{}".format(_slug(asset_id, "asset", 50), _slug(stem, "file", 40))
    candidate = "assets/{}{}".format(base, safe_extension)
    suffix = 2
    while candidate.casefold() in used:
        candidate = "assets/{}-{}{}".format(base, suffix, safe_extension)
        suffix += 1
    used.add(candidate.casefold())
    return candidate


def _asset_alt_text(record: Mapping[str, Any], asset_id: str, audience: str) -> Tuple[str, bool]:
    authored = record.get("alt_text")
    if isinstance(authored, str) and authored.strip():
        return authored.strip(), False

    kind = record.get("kind")
    kind_label = kind.strip() if isinstance(kind, str) and kind.strip() else "file"
    source_name = PurePosixPath(str(record.get("path") or asset_id)).name
    media_type = record.get("media_type")
    extension = PurePosixPath(source_name).suffix.casefold()
    renderable_image = (
        (isinstance(media_type, str) and media_type.casefold().startswith("image/"))
        or kind_label.casefold() in {"image", "map", "token", "portrait", "handout"}
        or extension in {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
    )
    if audience == "player" and renderable_image:
        raise AdapterError("player-visible renderable asset {} requires authored alt_text".format(asset_id))
    return (
        "{} asset {} ({}); no authored description was supplied.".format(
            kind_label[:1].upper() + kind_label[1:], asset_id, source_name
        ),
        True,
    )

def render_foundry_v14_bundle(
    projection: Mapping[str, Any],
    assets: Optional[AssetMap] = None,
    *,
    module_id: Optional[str] = None,
    module_title: Optional[str] = None,
) -> Dict[str, bytes]:
    asset_map = assets or {}
    module_id_value = _foundry_module_id(projection, module_id)
    title = _foundry_title(projection, module_title)
    loss_items: List[Dict[str, str]] = []
    files: Dict[str, bytes] = {}
    module_asset_paths: Dict[str, str] = {}
    asset_inventory: List[Dict[str, Any]] = []
    used_asset_paths = set()
    audience = projection.get("audience", "gm")
    if audience not in {"gm", "player"}:
        raise AdapterError("Foundry projection audience must be gm or player")
    for index, record in enumerate(sorted(_asset_records(projection), key=lambda item: str(item.get("id") or item.get("path") or "")), start=1):
        asset_id = record.get("id")
        if not isinstance(asset_id, str) or not asset_id:
            loss_items.append(_loss("warning", "asset-{}".format(index), "asset_omitted", "Asset record has no string id."))
            continue
        value = _asset_value(asset_map, record)
        if value is None:
            loss_items.append(_loss("warning", asset_id, "asset_omitted", "No bytes or readable path were supplied for this asset."))
            continue
        try:
            data = _coerce_asset_bytes(value, asset_id)
        except AdapterError as exc:
            loss_items.append(_loss("warning", asset_id, "asset_omitted", str(exc)))
            continue
        output_path = _asset_output_path(record, used_asset_paths)
        alt_text, used_alt_fallback = _asset_alt_text(record, asset_id, audience)
        if used_alt_fallback:
            loss_items.append(
                _loss(
                    "warning",
                    asset_id,
                    "asset_alt_text_fallback",
                    "No authored alt_text was supplied; a transparent filename-based fallback was emitted.",
                )
            )
        files[output_path] = data
        module_asset_paths[asset_id] = output_path
        asset_inventory.append({
            "sourceId": asset_id,
            "path": output_path,
            "altText": alt_text,
            "bytes": len(data),
            "sha256": _sha256(data),
        })

    journal_entries: List[Dict[str, Any]] = []
    roll_tables: List[Dict[str, Any]] = []
    scenes: List[Dict[str, Any]] = []
    used_source_ids = set()
    for index, obj in enumerate(sorted(_objects(projection), key=lambda item: str(item.get("id") or item.get("title") or "")), start=1):
        source_id = _source_id(obj, "object-{}".format(index))
        if source_id in used_source_ids:
            raise AdapterError("duplicate object source id: {}".format(source_id))
        used_source_ids.add(source_id)
        name = _object_name(obj)
        if name is None:
            name = source_id
            loss_items.append(_loss("warning", source_id, "source_id_used_as_name", "No explicit name or title was supplied."))
        kind = _object_kind(obj)
        if kind in _TABLE_KINDS:
            table = _roll_table_document(obj, source_id, name, loss_items)
            if table is not None:
                roll_tables.append(table)
            else:
                journal_entries.append(_journal_document(obj, source_id, name))
        elif kind in _SCENE_KINDS:
            scene = _scene_document(obj, source_id, name, module_id_value, module_asset_paths, loss_items)
            if scene is not None:
                scenes.append(scene)
            else:
                journal_entries.append(_journal_document(obj, source_id, name))
        else:
            journal_entries.append(_journal_document(obj, source_id, name))

    campaign_value = projection.get("campaign", {})
    campaign = campaign_value if isinstance(campaign_value, Mapping) else {}
    raw_campaign_id = campaign.get("id")
    campaign_id = raw_campaign_id.strip() if isinstance(raw_campaign_id, str) and raw_campaign_id.strip() else module_id_value
    ownership_default = 2 if audience == "player" else 0

    for document in journal_entries:
        document["ownership"] = {"default": ownership_default}
        _stamp_foundry_identity(document, campaign_id, audience)
        for page in document.get("pages", []):
            if isinstance(page, dict):
                _stamp_foundry_revision(page)
        _stamp_foundry_revision(document)
    for document in roll_tables:
        document["ownership"] = {"default": ownership_default}
        _stamp_foundry_identity(document, campaign_id, audience)
        _stamp_foundry_revision(document)
    for scene_record in scenes:
        scene_record["scene"]["ownership"] = {"default": ownership_default}
        _stamp_foundry_identity(scene_record, campaign_id, audience)
        for level in scene_record.get("levels", []):
            if isinstance(level, dict):
                _stamp_foundry_revision(level)
        _stamp_foundry_revision(scene_record, scene_record["scene"])

    payload = {
        "format": FOUNDRY_BUNDLE_FORMAT,
        "audience": audience,
        "target": {"generation": FOUNDRY_GENERATION, "build": FOUNDRY_BUILD},
        "compatibility": {
            "state": "statically_ready",
            "liveImportVerified": False,
        },
        "module": {"id": module_id_value, "title": title},
        "pack": {
            "id": campaign_id,
            "title": campaign.get("title") if isinstance(campaign.get("title"), str) and campaign.get("title") else title,
        },
        "source": {"projectionSha256": _sha256(_canonical_json_bytes(projection))},
        "documents": {
            "JournalEntry": journal_entries,
            "RollTable": roll_tables,
            "Scene": scenes,
        },
        "assets": asset_inventory,
    }
    manifest = {
        "id": module_id_value,
        "title": title,
        "type": "module",
        "description": "Offline Ludis campaign import bundle. Static compatibility only; live import is unverified.",
        "version": "1.0.0",
        "authors": [{"name": "Collaborative Dynamics"}],
        "compatibility": {"minimum": "14", "maximum": "14"},
        "esmodules": ["scripts/importer.mjs"],
        "media": [],
    }
    files["module.json"] = _pretty_json_bytes(manifest)
    files["scripts/importer.mjs"] = FOUNDRY_IMPORTER_TEMPLATE.replace("__LUDIS_MODULE_ID__", module_id_value).encode("utf-8")
    report = _loss_report(
        FOUNDRY_ADAPTER_ID,
        "Foundry VTT 14.365 core documents",
        loss_items,
        {
            "JournalEntry": len(journal_entries),
            "RollTable": len(roll_tables),
            "Scene": len(scenes),
            "Level": sum(len(scene["levels"]) for scene in scenes),
            "assets": len(asset_inventory),
        },
    )
    payload["compatibility"]["state"] = report["status"]
    files["data/ludis-foundry-v14.json"] = _pretty_json_bytes(payload)
    files["reports/loss-report.json"] = _pretty_json_bytes(report)
    validation_errors = validate_foundry_v14_bundle(files)
    if validation_errors:
        raise AdapterError("invalid Foundry adapter output: " + "; ".join(validation_errors))
    return files


def _foundry_ludis_metadata(document: Any) -> Optional[Mapping[str, Any]]:
    if not isinstance(document, Mapping):
        return None
    flags = document.get("flags")
    ludis = flags.get("ludis") if isinstance(flags, Mapping) else None
    return ludis if isinstance(ludis, Mapping) else None


def _foundry_source_id(document: Any) -> Optional[str]:
    ludis = _foundry_ludis_metadata(document)
    value = ludis.get("sourceId") if isinstance(ludis, Mapping) else None
    return value if isinstance(value, str) and value else None


def _validate_foundry_import_metadata(
    document: Any,
    label: str,
    campaign_id: Optional[str],
    audience: Any,
    errors: List[str],
    *,
    revision_source: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    ludis = _foundry_ludis_metadata(document)
    required = {"sourceId", "campaignId", "audience", "importRevisionSha256"}
    if ludis is None:
        errors.append("{}.flags.ludis is required".format(label))
        return None
    if set(ludis) != required:
        errors.append("{}.flags.ludis must contain only sourceId, campaignId, audience, and importRevisionSha256".format(label))
    source_id = ludis.get("sourceId")
    if not isinstance(source_id, str) or not source_id:
        errors.append("{}.flags.ludis.sourceId is required".format(label))
        source_id = None
    if ludis.get("campaignId") != campaign_id:
        errors.append("{}.flags.ludis.campaignId must match payload pack.id".format(label))
    if ludis.get("audience") != audience:
        errors.append("{}.flags.ludis.audience must match payload audience".format(label))
    revision = ludis.get("importRevisionSha256")
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{64}", revision) is None:
        errors.append("{}.flags.ludis.importRevisionSha256 must be a lowercase SHA-256".format(label))
    else:
        source = revision_source if revision_source is not None else document
        if isinstance(source, Mapping) and revision != _foundry_record_revision(source):
            errors.append("{}.flags.ludis.importRevisionSha256 does not match exact import record".format(label))
    return source_id


def validate_foundry_v14_bundle(files: Mapping[str, bytes]) -> List[str]:
    errors: List[str] = []
    required_members = {
        "module.json",
        "scripts/importer.mjs",
        "data/ludis-foundry-v14.json",
        "reports/loss-report.json",
    }
    for path in files:
        if not _safe_member_path(path):
            errors.append("unsafe output path: {}".format(path))
        suffix = PurePosixPath(path).suffix.casefold()
        if suffix in {".js", ".mjs", ".cjs"} and path != "scripts/importer.mjs":
            errors.append("unexpected executable Foundry bundle member: {}".format(path))
    for required in sorted(required_members):
        if required not in files:
            errors.append("missing required Foundry bundle member: {}".format(required))

    manifest = _decode_json(files, "module.json", errors)
    payload = _decode_json(files, "data/ludis-foundry-v14.json", errors)
    report = _decode_json(files, "reports/loss-report.json", errors)

    module_id = None
    if isinstance(manifest, dict):
        allowed_manifest_keys = {
            "id",
            "title",
            "type",
            "description",
            "version",
            "authors",
            "compatibility",
            "esmodules",
            "media",
        }
        if set(manifest) != allowed_manifest_keys:
            unexpected = sorted(set(manifest) - allowed_manifest_keys)
            missing = sorted(allowed_manifest_keys - set(manifest))
            errors.append("module.json keys do not match the strict allowlist; unexpected={} missing={}".format(unexpected, missing))
        module_id = manifest.get("id")
        if not isinstance(module_id, str) or not _SAFE_MODULE_ID.fullmatch(module_id):
            errors.append("module.json id is invalid")
        if manifest.get("type") != "module":
            errors.append("module.json type must be module")
        if not isinstance(manifest.get("title"), str) or not manifest["title"].strip():
            errors.append("module.json title is required")
        if manifest.get("description") != "Offline Ludis campaign import bundle. Static compatibility only; live import is unverified.":
            errors.append("module.json description does not match the generated contract")
        if manifest.get("version") != "1.0.0":
            errors.append("module.json version must be 1.0.0")
        if manifest.get("authors") != [{"name": "Collaborative Dynamics"}]:
            errors.append("module.json authors do not match the generated contract")
        compatibility = manifest.get("compatibility")
        if compatibility != {"minimum": "14", "maximum": "14"}:
            errors.append("module.json must contain only the generation 14 compatibility bounds")
        if manifest.get("esmodules") != ["scripts/importer.mjs"]:
            errors.append("module.json esmodules must contain only scripts/importer.mjs")
        if manifest.get("media") != []:
            errors.append("module.json media must be the generated empty array")

    importer = files.get("scripts/importer.mjs")
    if not isinstance(importer, bytes):
        errors.append("scripts/importer.mjs must be bytes")
    elif isinstance(module_id, str) and _SAFE_MODULE_ID.fullmatch(module_id):
        expected_importer = FOUNDRY_IMPORTER_TEMPLATE.replace("__LUDIS_MODULE_ID__", module_id).encode("utf-8")
        if importer != expected_importer:
            errors.append("scripts/importer.mjs does not exactly match the trusted generated importer for module.json id")

    if isinstance(report, dict):
        if report.get("format") != LOSS_REPORT_FORMAT or report.get("adapter") != FOUNDRY_ADAPTER_ID:
            errors.append("Foundry loss report identity is invalid")
        _validate_loss_report_compatibility(report, "Foundry loss report", errors)

    if not isinstance(payload, dict):
        return errors
    allowed_payload_keys = {
        "format",
        "audience",
        "target",
        "compatibility",
        "module",
        "pack",
        "source",
        "documents",
        "assets",
    }
    if set(payload) != allowed_payload_keys:
        errors.append("Foundry payload keys do not match the static contract")
    if payload.get("format") != FOUNDRY_BUNDLE_FORMAT:
        errors.append("Foundry payload format is invalid")
    audience = payload.get("audience")
    if audience not in {"gm", "player"}:
        errors.append("Foundry payload audience must be gm or player")
    expected_ownership = 2 if audience == "player" else 0
    target = payload.get("target")
    if target != {"generation": FOUNDRY_GENERATION, "build": FOUNDRY_BUILD}:
        errors.append("Foundry payload must target generation 14 build 365")
    payload_compatibility = payload.get("compatibility")
    report_status = report.get("status") if isinstance(report, dict) else None
    if payload_compatibility != {"state": report_status, "liveImportVerified": False}:
        errors.append("Foundry payload compatibility state must exactly match the loss report status")
    module = payload.get("module")
    if not isinstance(module, dict) or set(module) != {"id", "title"} or module.get("id") != module_id:
        errors.append("Foundry payload module must exactly match module.json identity")
    pack = payload.get("pack")
    campaign_id: Optional[str] = None
    if not isinstance(pack, dict) or set(pack) != {"id", "title"}:
        errors.append("Foundry payload pack must contain only id and title")
    else:
        raw_campaign_id = pack.get("id")
        if isinstance(raw_campaign_id, str) and raw_campaign_id:
            campaign_id = raw_campaign_id
        else:
            errors.append("Foundry payload pack.id is required")
        if not isinstance(pack.get("title"), str) or not pack["title"]:
            errors.append("Foundry payload pack.title is required")
    source = payload.get("source")
    projection_digest = source.get("projectionSha256") if isinstance(source, dict) and set(source) == {"projectionSha256"} else None
    if not isinstance(projection_digest, str) or re.fullmatch(r"[0-9a-f]{64}", projection_digest) is None:
        errors.append("Foundry payload source must contain only a lowercase projectionSha256")

    documents = payload.get("documents")
    if not isinstance(documents, dict) or set(documents) != {"JournalEntry", "RollTable", "Scene"}:
        errors.append("Foundry payload documents must contain only JournalEntry, RollTable, and Scene")
        return errors

    all_ids = set()
    for document_type in ("JournalEntry", "RollTable"):
        records = documents.get(document_type)
        if not isinstance(records, list):
            errors.append("documents.{} must be an array".format(document_type))
            continue
        for index, document in enumerate(records):
            label = "documents.{}[{}]".format(document_type, index)
            if not isinstance(document, dict):
                errors.append("{} must be an object".format(label))
                continue
            source_id = _validate_foundry_import_metadata(document, label, campaign_id, audience, errors)
            if source_id is not None:
                identity = (campaign_id, source_id)
                if identity in all_ids:
                    errors.append("duplicate Foundry campaign/source identity: {}/{}".format(campaign_id, source_id))
                else:
                    all_ids.add(identity)
            if not isinstance(document.get("name"), str) or not document["name"].strip():
                errors.append("{}.name is required".format(label))
                continue
            ownership = document.get("ownership")
            if ownership != {"default": expected_ownership}:
                errors.append("{}.ownership must contain only the audience-matching default".format(label))
            if document_type == "JournalEntry":
                pages = document.get("pages")
                if not isinstance(pages, list) or not pages:
                    errors.append("{}.pages must be a non-empty array".format(label))
                else:
                    for page_index, page in enumerate(pages):
                        page_label = "{}.pages[{}]".format(label, page_index)
                        text = page.get("text") if isinstance(page, dict) else None
                        if not isinstance(page, dict) or page.get("type") != "text" or not isinstance(text, dict) or text.get("format") not in {1, 2}:
                            errors.append("{} must be a text page with format 1 or 2".format(page_label))
                            continue
                        page_id = _validate_foundry_import_metadata(page, page_label, campaign_id, audience, errors)
                        if page_id is not None:
                            page_identity = (campaign_id, page_id)
                            if page_identity in all_ids:
                                errors.append("duplicate Foundry campaign/source identity: {}/{}".format(campaign_id, page_id))
                            else:
                                all_ids.add(page_identity)
            else:
                formula = document.get("formula")
                match = re.fullmatch(r"1d([1-9][0-9]*)", formula) if isinstance(formula, str) else None
                results = document.get("results")
                if match is None or not isinstance(results, list) or not results:
                    errors.append("{} must have a 1dN formula and results".format(label))
                else:
                    expected = set(range(1, int(match.group(1)) + 1))
                    covered = set()
                    for result_index, result in enumerate(results):
                        result_label = "{}.results[{}]".format(label, result_index)
                        if not isinstance(result, dict) or result.get("type") != "text" or not isinstance(result.get("text"), str):
                            errors.append("{} must be a text result".format(result_label))
                            continue
                        weight = _positive_int(result.get("weight"))
                        range_value = result.get("range")
                        if weight is None or not isinstance(range_value, list) or len(range_value) != 2:
                            errors.append("{} has invalid weight or range".format(result_label))
                            continue
                        low, high = range_value
                        if not isinstance(low, int) or not isinstance(high, int) or low < 1 or high < low or high - low + 1 != weight:
                            errors.append("{} range does not match weight".format(result_label))
                            continue
                        values = set(range(low, high + 1))
                        if covered & values:
                            errors.append("{} overlaps another result range".format(result_label))
                        covered |= values
                    if covered != expected:
                        errors.append("{} result ranges do not exactly cover its formula".format(label))

    scene_records = documents.get("Scene")
    if not isinstance(scene_records, list):
        errors.append("documents.Scene must be an array")
        scene_records = []
    for index, record in enumerate(scene_records):
        label = "documents.Scene[{}]".format(index)
        if not isinstance(record, dict):
            errors.append("{} must be an object".format(label))
            continue
        if set(record) != {"sourceId", "scene", "levels", "initialLevelSourceId"}:
            errors.append("{} keys do not match the scene import contract".format(label))
        scene = record.get("scene")
        source_id = record.get("sourceId")
        validated_source_id = _validate_foundry_import_metadata(
            scene,
            "{}.scene".format(label),
            campaign_id,
            audience,
            errors,
            revision_source=record,
        )
        if not isinstance(source_id, str) or validated_source_id != source_id:
            errors.append("{} has inconsistent flags.ludis.sourceId".format(label))
        else:
            identity = (campaign_id, source_id)
            if identity in all_ids:
                errors.append("duplicate Foundry campaign/source identity: {}/{}".format(campaign_id, source_id))
            else:
                all_ids.add(identity)
        if not isinstance(scene, dict):
            errors.append("{}.scene must be an object".format(label))
            continue
        ownership = scene.get("ownership")
        if ownership != {"default": expected_ownership}:
            errors.append("{}.scene.ownership must contain only the audience-matching default".format(label))
        if "background" in scene:
            errors.append("{}.scene uses obsolete top-level background instead of a v14 Level".format(label))
        if _positive_int(scene.get("width")) is None or _positive_int(scene.get("height")) is None:
            errors.append("{}.scene width and height must be positive integers".format(label))
        levels = record.get("levels")
        if not isinstance(levels, list) or not levels:
            errors.append("{}.levels must be a non-empty array".format(label))
            continue
        level_ids = set()
        for level_index, level in enumerate(levels):
            level_label = "{}.levels[{}]".format(label, level_index)
            level_id = _validate_foundry_import_metadata(level, level_label, campaign_id, audience, errors)
            identity = (campaign_id, level_id) if level_id is not None else None
            if level_id is None or level_id in level_ids or identity in all_ids:
                errors.append("{} has a missing or duplicate flags.ludis.sourceId".format(level_label))
            else:
                level_ids.add(level_id)
                all_ids.add(identity)
            background = level.get("background") if isinstance(level, dict) else None
            src = background.get("src") if isinstance(background, dict) else None
            prefix = "modules/{}/".format(module_id) if isinstance(module_id, str) else "modules/"
            if not isinstance(src, str) or not src.startswith(prefix):
                errors.append("{} background must be module-relative".format(level_label))
            else:
                member = src[len(prefix):]
                if member not in files:
                    errors.append("{} background asset is missing: {}".format(level_label, member))
        if record.get("initialLevelSourceId") not in level_ids:
            errors.append("{}.initialLevelSourceId must identify one bundled Level".format(label))

    inventory = payload.get("assets")
    inventory_paths = set()
    if not isinstance(inventory, list):
        errors.append("Foundry payload assets must be an array")
    else:
        for index, item in enumerate(inventory):
            label = "assets[{}]".format(index)
            if not isinstance(item, dict) or set(item) != {"sourceId", "path", "altText", "bytes", "sha256"}:
                errors.append("{} must contain only sourceId, path, altText, bytes, and sha256".format(label))
                continue
            alt_text = item.get("altText")
            if not isinstance(alt_text, str) or not alt_text.strip() or alt_text != alt_text.strip():
                errors.append("{}.altText must be a non-empty canonical string".format(label))
            path = item.get("path")
            if not isinstance(path, str) or not path.startswith("assets/") or path not in files:
                errors.append("{}.path does not name a bundled asset".format(label))
                continue
            data = files[path]
            if item.get("bytes") != len(data) or item.get("sha256") != _sha256(data):
                errors.append("{} size or digest does not match bundled bytes".format(label))
            if path in inventory_paths:
                errors.append("duplicate asset inventory path: {}".format(path))
            inventory_paths.add(path)
        actual_asset_paths = {path for path in files if path.startswith("assets/")}
        if inventory_paths != actual_asset_paths:
            errors.append("Foundry asset inventory does not exactly match bundled assets")

    permitted_members = required_members | inventory_paths
    unexpected_members = sorted(set(files) - permitted_members)
    if unexpected_members:
        errors.append("Foundry bundle contains unlisted members: {}".format(", ".join(unexpected_members)))
    return errors