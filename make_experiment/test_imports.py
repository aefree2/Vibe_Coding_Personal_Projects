from get_imports  import  find_imports
import re
from typing import Dict, List, Tuple, Optional
import json
import os
from os import environ

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional



if __name__ == "__main__":
   find_imports("url", "commit", "dir_name", "test_for_imports.py", "test_imports.csv") #confirmed that it will get top level files. 
    #TODO: need to decide how to handle from x import y, because I want both x and y..., will make this decision later 