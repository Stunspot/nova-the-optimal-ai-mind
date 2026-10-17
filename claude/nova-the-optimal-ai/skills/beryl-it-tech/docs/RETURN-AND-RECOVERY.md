# Return to your saved bench

Use **Exit** to finish a session, wait for **Beryl is closed**, then reopen the same shortcut. Samples, selected originals, investigation history and your selected view remain in the saved folder shown at the bottom of the companion.

If an observation is running, choose **Cancel observation** and wait before Exit. If a selected file is being retained, let that operation finish. Exit explains when an operation still needs to end.

## Reconnect after closing a tab

Reopen the same shortcut. A running instance is reused when its identity and saved folder match. Closing the last tab leaves a 90-second grace for reload or reconnection before the owned local service stops; another open companion tab keeps the service in use. Use Exit when you want confirmed closure.

If the companion reports disconnection, preserve the saved folder and reopen its shortcut. An error message or lost browser tab is not evidence that your stored material was replaced. Read the current message before trying another action.

## When the saved bench is unavailable

Choose **Try opening again** once if the saved-bench screen offers it. If the problem remains, keep the saved folder intact and ask Beryl to inspect the reported error and recovery path. Do not delete the folder to make the error disappear.

An explicitly selected data folder must already exist and be writable, outside the installed program. If the launcher says it is missing, locate the intended saved folder before relaunching; do not silently substitute an empty folder and expect previous work to appear.

The known prior Beryl location on Windows is `%LOCALAPPDATA%/Collaborative Dynamics/beryl-it-benchcraft`, unless an explicit data-home option or `BERYL_WORK_HOME` selects another location. The companion reads legacy `work.json` only from the chosen known home. It retains the original, extension fields and embedded attachments; a failed legacy import is explained without rewriting that file.

## Preserve a whole saved folder

After confirmed Exit, copy the entire saved folder to your chosen backup location. Keep `bench.json` together with `originals`; the store's links depend on those retained originals. Preserve existing `work.json` and any other legacy material as part of the same backup. Copying only a downloaded original does not preserve investigations or view history.

When moving the bench, use an existing writable destination outside the installed program and have the local assistant point the launcher at that folder. Reopen it, confirm the intended investigations and originals are present, then retain the original backup until the move is checked.

## When a measure or source is unavailable

Read the reason attached to the field. A partially unavailable observation can still retain the other actual results. The fixed live observation is Windows-only; prepared investigations and retained sources remain readable without it.

If a source preview is incomplete, use the retained exact original with Beryl. If an original cannot be read, keep the investigation history and identify the missing material in conversation before relying on the affected interpretation.

Return to [first use](FIRST-USE.md) or [the investigation-reading guide](READ-AN-INVESTIGATION.md).
