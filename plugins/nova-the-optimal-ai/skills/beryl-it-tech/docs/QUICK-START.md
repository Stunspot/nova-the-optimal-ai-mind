# Begin with one real problem

In your Agent host, invoke `$beryl-it-tech` and describe the device, what happens, when it happens and what you need to do. For example: “My dock loses Ethernet after wake; Wi-Fi still works. Help me find a safe next test.” Say whether changes are permitted. Do not supply passwords or recovery keys.

A useful first response separates your reported facts from unknowns, identifies any safety/data/authority boundary, and gives one observation that can change the diagnosis. It need not invent a cause. A simple reversible task should not demand a full formal case.

For a visual record, open `workspace/Open.cmd` on Windows or run `python -B workspace/host.py` from this skill folder with Python 3.10 or newer. Select **Start a case**, enter the device, reported behavior and desired outcome, then **Create working case**. Owner/scope and risk can remain unknown. This creates an incomplete intake with no invented hypotheses, test results or permission.

Select **Download copy** and confirm the JSON reached your files. Attach that file when asking Beryl to continue. The Studio itself displays and edits records; it does not converse, diagnose or execute device commands. **Explore example** is explicitly synthetic. See [case files](CASE-FILES.md) and [the user guide](USER-GUIDE.md) for the next turn.
