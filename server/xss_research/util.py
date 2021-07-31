import logging
import os
import subprocess
import sys
from contextlib import contextmanager

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# cf. https://stackoverflow.com/a/37996581
@contextmanager
def cwd(path: str):
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)

@contextmanager
def git_checkout(commit: str):
    p = subprocess.run(["git", "--no-pager", "rev-parse", "HEAD"], capture_output=True)
    oldcommit = p.stdout.decode('utf-8').strip()
    logger.debug(f"Saving old commit: {oldcommit}")

    logger.debug(f"Checking out commit: {commit}")
    subprocess.run(["git", "checkout", commit])
    try:
        yield
    finally:
        logger.debug(f"Returning to commit: {oldcommit}")
        subprocess.run(["git", "checkout", oldcommit])