# app/utils/logger.py

import logging
import os
<<<<<<< HEAD
import logging
=======
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

log_dir = "tests/logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "processor.log")

logger = logging.getLogger("root")
logger.setLevel(logging.INFO)

fh = logging.FileHandler(log_path)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
<<<<<<< HEAD
=======


def get_logger():
    """Returns the configured logger instance"""
    return logger
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
