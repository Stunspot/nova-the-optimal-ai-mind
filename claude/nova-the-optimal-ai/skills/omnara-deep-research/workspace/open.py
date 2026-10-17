from pathlib import Path
import sys

# Bind imports to this workspace explicitly. The service child executes this
# same file and must not depend on cwd or Python implicit script paths.
workspace = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(workspace))
sys.path.insert(1, str(workspace.parent / 'scripts'))

from omnara_app import OmnaraWorkspace
from runtime import launch

if __name__ == '__main__':
    launch(
        'omnara',
        'OMNARA Campaigns',
        lambda root: OmnaraWorkspace(root, workspace.parent / 'examples' / 'sea-level-comparison'),
        workspace,
    )

