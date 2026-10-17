from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]
os.environ['THEHARVESTER_SCHEDULER'] = 'disabled'
from theHarvester.lib import core, database
core.CONFIG_DIRS = [ROOT / 'config' / 'theharvester']
database._DEFAULT_DATABASE = ROOT / 'state' / 'theharvester' / 'stash.sqlite'
from theHarvester.theHarvester import main
if __name__ == '__main__':
    main()
