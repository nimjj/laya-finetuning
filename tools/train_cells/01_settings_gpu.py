# CELL 1: settings + GPU check.
# EXPECT: "NVIDIA L4, 23034 MiB" (about 23 GB), "cuda True", then the run id.
import datetime
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

import torch

BASE_REPO = "convaiinnovations/laya"
BASE_REV = "7b928d828b7b0e022f929d9bd2e44165aa270148"      # the snapshot used locally (laya-test/hf_home)
LAYA_COMMIT = "3cf26cbcb18725dbc2d127bb8bb2c4c43243ae63"   # laya v0.4.0
LOCAL_BASE_SHA256 = {
    "model.safetensors": "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c",
    "rl_agent_config.json": "ae287b56bbcf5f8c4f4541ae9dfd00c914c4c48b940b8398c3058af37ba92bbd",
}
TRAINED = ["rapport", "paraphrasing", "active_listening", "resolved", "empathy"]    # checks this fine-tune is meant to improve
REGRESSION = ["ownership", "probing", "hostility", "escalation"]                     # checks that must not get worse

DRIVE = "/content/drive/MyDrive/laya-finetuning"
WORK = "/content/work"
os.makedirs(WORK, exist_ok=True)

# one run id per session, kept on disk so re-running this cell does not change it
_rid = f"{WORK}/run_id.txt"
if not os.path.exists(_rid) or not open(_rid).read().startswith("{{RUN_PREFIX}}"):      # never reuse an older run's id (or the smoke test's)
    open(_rid, "w").write("{{RUN_PREFIX}}" + datetime.datetime.now().strftime("%Y%m%d-%H%M"))
RUN_ID = open(_rid).read().strip()

print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                     capture_output=True, text=True).stdout.strip())
print("cuda", torch.cuda.is_available(), "| torch", torch.__version__)
print("run id:", RUN_ID)
