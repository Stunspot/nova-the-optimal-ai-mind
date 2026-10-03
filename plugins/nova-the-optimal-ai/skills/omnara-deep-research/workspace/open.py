from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from campaign import CampaignRoom
from runtime import launch
if __name__=='__main__': launch('omnara','OMNARA Campaigns',CampaignRoom,Path(__file__).parent)
