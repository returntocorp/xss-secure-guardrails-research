import logging
import json
import os
import subprocess
import sys
from database import db
from app import app
from util import cwd, git_checkout
from models import Finding, TriageStatus

from typing import Any

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

with app.app_context():
    db.create_all()

def get_diff_text(directory: str, previous_commit: str, fix_commit: str) -> str:
    with cwd(directory):
        p = subprocess.run(["git", "--no-pager", "diff", f"{previous_commit}..{fix_commit}"], capture_output=True)
        diff_text = p.stdout
    return diff_text.decode('utf-8')

def get_semgrep_results(directory: str, commit: str, config: str) -> str:
    with cwd(directory):
        with git_checkout(commit):
            p = subprocess.run(["semgrep", "-f", config], stdout=subprocess.PIPE)
            results = p.stdout.decode('utf-8')
    return results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fix-commit", "-x", default="HEAD")
    parser.add_argument("--previous-commit", "-p", default="HEAD~1")
    parser.add_argument("--dryrun", "-z", action="store_true")
    parser.add_argument("directory")

    args = parser.parse_args()

    CONFIG_URL = "p/xss"

    diff_text = get_diff_text(args.directory, args.previous_commit, args.fix_commit)
    semgrep_results_on_diff = get_semgrep_results(args.directory, args.fix_commit, CONFIG_URL)
    previous_semgrep_results = get_semgrep_results(args.directory, args.previous_commit, CONFIG_URL)
    finding = Finding(
        repo_url = args.directory,
        fix_commit = args.fix_commit,
        previous_commit = args.previous_commit,
        diff_text = diff_text,
        semgrep_results_on_diff = semgrep_results_on_diff,
        triage_status = TriageStatus(0),
        reviewer_notes = "",
    )
    if args.dryrun:
        print(finding.fix_semgrep_results)
        print(finding.previous_semgrep_results)
    else:
        with app.app_context():
            db.session.add(finding)
            db.session.commit()