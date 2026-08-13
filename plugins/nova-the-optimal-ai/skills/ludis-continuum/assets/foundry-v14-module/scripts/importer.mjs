const MODULE_ID = "__LUDIS_MODULE_ID__";
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
