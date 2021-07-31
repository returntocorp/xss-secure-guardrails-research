import argparse
import json
import logging
import pandas as pd
import os
import requests
import subprocess
import sys
import math
from sqlalchemy.orm.exec import MultipleResultsFound
from app import app
from models import Finding, TriageStatus
from util import cwd, git_checkout
from database import db

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

DOWNLOADED_REPO_DIRECTORY = "downloaded_repos"
PACK_URL = "https://semgrep.dev/c/p/xss"
LOCAL_RULESET_FILE = os.path.join(os.getcwd(), "semgrep.yaml")
LEN_CMD = 3

SUPPORTED_LANG_EXTS_XSS = [
    ".go",
    ".java",
    ".js",
    ".json",
    ".py",
    ".rb",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".erb",
    ".jsp",
    ".yml"
]

with app.app_context():
    db.create_all()

def parse_args():
    args = argparse.ArgumentParser(
        description="""
            Automates the process of triaging XSS research results by generating
            diffs of semgrep runs on parent and child commits, along with the
            git diffs if needed.
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    args.add_argument(
        "-i",
        "--input",
        action="store",
        required=True,
        help="The JSON file containing information on bigQuery results."
    )

    args.add_argument(
        "--diffs-only",
        action="store_true",
        required=False,
        help="Only run semgrep on the diffs between the two commits."
    )

    return args.parse_args()

def download_ruleset(ruleset_url: str, download_path: str = LOCAL_RULESET_FILE) -> str:
    logger.info(f"Downloading ruleset '{ruleset_url}' to file '{download_path}'")
    with open(download_path, 'w') as fout:
        fout.write(requests.get(ruleset_url).text)
    return os.path.abspath(download_path)

def download_repo(row, path: str):
    repo_name = row["repository"]
    git_url = "https://github.com/" + repo_name + ".git"
    logger.info(f"Downloading repo '{git_url}'")
    # download repositories and semgrep diff/ git diff them
    with cwd(DOWNLOADED_REPO_DIRECTORY):
        subprocess.run(["git", "clone", git_url, repo_name])

def get_diff_text(path: str, old_commit: str, new_commit: str) -> str:
    logger.info(f"Running git diff on '{path}'")
    with cwd(path):
        p = subprocess.run(["git", "--no-pager", "diff", old_commit, new_commit], capture_output=True)
        if p.returncode != 0:
            return "git diff run returned an error."
        diff_text = p.stdout
    try:
        return diff_text.decode('utf-8')
    except UnicodeDecodeError:
        return "Couldn't decode git diff output."

def get_git_diff_files(path: str, old_commit: str, new_commit: str):
    with cwd(path):
        p = subprocess.run(["git", "diff", "--name-only", old_commit, new_commit], stdout=subprocess.PIPE)
        if p.returncode != 0:
            return "git diff for files only returned an error."
        try:
            git_diff_files = p.stdout.decode('utf-8')
        except UnicodeDecodeError:
            return "Couldn't decode git diff files."

    git_diff_list = list(git_diff_files.split("\n"))
    if len(git_diff_list) > 0:
        git_diff_list = git_diff_list[:-1]
    return git_diff_list

def lang_supported(git_diff_files: list) -> bool:
    # if more than 20% of files is of an extension we don't support, skip.
    unsupported_files = 0
    max_unsupported_files = math.floor(len(git_diff_files)/5)
    for file in git_diff_files:
        filename, file_extension = os.path.splitext(file)
        if not file_extension in SUPPORTED_LANG_EXTS_XSS:
            unsupported_files += 1
        if unsupported_files > max_unsupported_files:
            logger.info(f"This repository has {unsupported_files} file(s) in languages that are not supported.")
            return False
    return True

def get_semgrep_results(path: str, old_commit: str, new_commit: str) -> str:
    git_diff_list = get_git_diff_files(path, old_commit, new_commit)
    # if git diff list doesn't return error, run lang_supported.
    if (type(git_diff_list) != str):
        if (not lang_supported(git_diff_list)):
            return "Not Supported."
    with cwd(path):
        with git_checkout(old_commit):
            p = subprocess.run(["semgrep", "-f", LOCAL_RULESET_FILE], stdout=subprocess.PIPE)
            try:
                results = p.stdout.decode('utf-8')
            except UnicodeDecodeError:
                return "Could not decode git diff output."
    return results

def get_semgrep_results_for_changed_files(path: str, old_commit: str, new_commit: str)-> str:
    # get files that had diffs.
    logger.info(f"Running Semgrep on '{path}'")
    git_diff_list = get_git_diff_files(path, old_commit, new_commit)
    if (not lang_supported(git_diff_list)):
        return "Not Supported."

    with cwd(path):
        with git_checkout(old_commit):
            cmd = ['semgrep', '--config', LOCAL_RULESET_FILE]
            for file_name in git_diff_list:
                file_name = file_name.strip()
                # check if the file exists in the old directory
                if os.path.exists(file_name):
                    cmd.append(file_name)
            if (len(cmd) == LEN_CMD):
                return "Only added files diff'ed."
            p = subprocess.run(cmd, stdout=subprocess.PIPE)
            if p.returncode != 0:
                return "semgrep run returned an error."
    try:
        return p.stdout.decode('utf-8')
    except UnicodeDecodeError:
        return "Couldn't decode semgrep output."

def post_to_db(row, git_diff_text: str, semgrep_diff_text: str):
    repo_name = row["repository"]
    repo_url = "https://github.com/" + repo_name
    row_to_add = Finding(
        repo_url=repo_url,
        repo_message=row["message"],
        fix_commit=row["commit"],
        previous_commit= row["parent"][0],
        diff_text=git_diff_text,
        semgrep_results_on_diff=semgrep_diff_text,
        triage_status=TriageStatus(0),
        reviewer_notes="",
    )
    with app.app_context():
        db.session.add(row_to_add)
        db.session.commit()

def analyze_repos(table, diffs_only: bool):
    download_ruleset(PACK_URL, LOCAL_RULESET_FILE)
    for index, row in table.iterrows():
        repo_name = row["repository"]
        repo_path = os.path.join(DOWNLOADED_REPO_DIRECTORY, repo_name)
        repo_url = "https://github.com/" + repo_name
        # first check if repo already in db. If it is, skip.
        with app.app_context():
            try:
                repo_exists = db.session.query(Finding.id).filter(
                    Finding.repo_url==repo_url,
                    Finding.fix_commit==row["commit"]).scalar()
            except MultipleResultsFound:
                repo_exists = 1
        if not repo_exists is None:
            logger.info(f"Skipping '{repo_name} because it is already in the database.")
            continue
        if not os.path.exists(repo_path):
            logger.info(f"Repository '{repo_name}' has not been downloaded. Downloading...")
            logger.info(f"Creating directory '{repo_path}'")
            os.makedirs(repo_path)
            download_repo(row, repo_path)

        git_diff_text = get_diff_text(repo_path, row["parent"][0], row["commit"])
        if diffs_only:
            semgrep_diff_text = get_semgrep_results_for_changed_files(repo_path, row["parent"][0], row["commit"])
        else:
            semgrep_diff_text = get_semgrep_results(repo_path, row["parent"][0], row["commit"])
        if not semgrep_diff_text == "Not Supported.":
            post_to_db(row, git_diff_text, semgrep_diff_text)

def main() -> None:
    args = parse_args()
    # transform json dump into table
    table = pd.read_json(args.input, orient="split")
    analyze_repos(table, args.diffs_only)

if __name__ == "__main__":
    main()
