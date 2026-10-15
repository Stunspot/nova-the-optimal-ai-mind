# Add an Omnara entry

The complete package contains browser icons plus Windows ICO and Mac ICNS files derived from the approved Omnara globe artwork. The room and public site use the same recognizable icon.

Create an entry only when you want one. From the stable extracted package, choose an existing destination directory:

```text
python -B workspace/create_entry.py --directory "your chosen directory" --platform windows
python3 -B workspace/create_entry.py --directory "your chosen directory" --platform mac
```

Windows creates OMNARA.lnk pointing to this package's Open.cmd with its ICO. Mac creates OMNARA.app with an ICNS-bound Info.plist and an executable launcher that opens this package's Open.command. Python 3.10+ remains required. The Windows command must run on Windows; Mac bundle construction can run on either platform.

The helper refuses an existing entry, linked package/destination paths and missing launchers/icons. It writes only the requested new entry; it does not launch the room or alter research, OMNARA_HOME, existing services or browser preferences. A failed Mac construction stays available for inspection.

Keep the extracted package at its stable location. If you move or remove it, create a new entry at a new path for that installation. Remove only the entry you created to uninstall that entry; leave your separate research home intact. Normal launch and data selection remain in [the room guide](CAMPAIGN-ROOM.md).

Entries inherit OMNARA_HOME from their launch environment, or use Documents/OMNARA Campaigns. A prior CLI --data-root choice is not stored in an entry. Keep using the original launcher with --data-root for that explicit home, or supply OMNARA_HOME in the environment that launches the entry.
