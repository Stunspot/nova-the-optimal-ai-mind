# Keep a working answer current

Open `workspace/Open.cmd` on Windows, or `workspace/Open.command` on macOS, from the AnswerLayer skill folder. Python 3 and a modern browser are required. The app opens **Working answers** with your saved answers, or a direct way to track the first one. No prepared JSON is required.

Choose **Track an answer**. Give it a useful name, paste the wording you rely on, and state who uses it and for what decision. Record the information cutoff and confidence if you know them. **Save working answer** keeps the reference privately on this computer.

Use **Add a development** for a new fact, correction, upcoming change, confidence change, or question. Keep the relevant passage beside its source and location. Mark it examined only when you actually examined that passage or observation. The optional supporting file is a private copy, up to 5 MB; the app does not extract its meaning or verify its claims. A future effective date remains visible as future rather than becoming current guidance automatically.

Write the proposed wording, confidence, or practical action that should change, and explain why. Leave a proposed field blank to keep its current value. An action-only change can be adopted without rewriting the answer. Capture scope, confidence, practical action, what could reverse the conclusion, and the next check. **Compare wording** marks removals and additions. A valid conclusion may be no change: save the evidence and return point without adopting a revision.

An optional revised information cutoff states how current your evidence is; leaving it blank preserves the existing cutoff. The local adoption timestamp never silently becomes the information cutoff.

**Adopt as my local answer** retains the prior wording, revised wording, reasoning, and evidence snapshot in history. It changes your local working answer only. It does not publish, approve a governed patch, or contact a source. Direct edits to the current reference are saved as working edits; use adoption when you need a before-and-after revision record.

Put the next useful question in working notes and set a review date if helpful. The date is a return point, not an automatic reminder. **Download answer brief** gives you readable Markdown with the current answer, developments, proposed change, adoption history, and next check.

## Save, move, and recover

Form buttons explicitly save your answer and visible draft fields. The status tells you whether saving succeeded. The private data location appears in the footer; Windows defaults to your writable local application data, outside the installed skill. You can launch with `--data-home "E:\My AnswerLayer Work"` to select another writable location. Existing answers are loaded from that selected location; unrelated folders are never scanned.

**Back up workspace** downloads answers, drafts, history, and supporting files. **Restore backup** adds restored copies, preserving existing answers. A workspace is limited to 200 answers and 40 MB. Keep large source originals separately and record their location. A malformed backup is rejected. If another window saved first, the older window cannot overwrite it: download its backup, reload current work, then restore and reconcile the copies.

If saved work cannot be read, preserve `work.json` from the stated data location. Launch with a new writable `--data-home` folder and restore a known-good backup. Do not replace a damaged original while investigating it.

## Existing native records

**Advanced native records** opens the retained Reality Ledger viewer and exact JSON editor. Its native JSON import, validation, and export remain available. That advanced viewer still works on a temporary imported record and requires downloading edits. Its governed approval/adoption assertions and the command-line ledger are distinct from the simple local working-answer history. Neither interface establishes source truth or publication authority.

The local app provides an organized comparison and durable working memory. Research, source interpretation, and judgment come from you or an actual AnswerLayer conversation; no AI reply is generated in this app.
