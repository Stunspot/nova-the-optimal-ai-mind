"""Dispatch OMNARA's authoring vault and read-only reading room explicitly."""
from pathlib import Path
from campaign import CampaignRoom
from reading_room import ReadOnlyRoom

class OmnaraWorkspace:
    class Conflict(CampaignRoom.Conflict):
        pass

    def __init__(self, root: Path, example_root: Path | None = None):
        self.campaigns = CampaignRoom(root)
        self.reader = ReadOnlyRoom(root, example_root)

    def request(self, method: str, path: str, data: dict):
        if path.startswith('/api/reader/'):
            try:
                return self.reader.request(method, path, data)
            except ReadOnlyRoom.Conflict as exc:
                raise self.Conflict(str(exc)) from exc
        return self.campaigns.request(method, path, data)
