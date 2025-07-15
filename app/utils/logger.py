# app/utils/logger.py

import os
import logging

log_dir = "tests/logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "processor.log")

logger = logging.getLogger("root")
logger.setLevel(logging.INFO)

fh = logging.FileHandler(log_path)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
