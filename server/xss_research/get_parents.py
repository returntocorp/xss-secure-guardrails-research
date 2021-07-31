import argparse
import os
import logging
import json
import subprocess
import sys
import pandas as pd
from app import app
from util import cwd
from models import Finding, TriageStatus
from database import db

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

DOWNLOADED_REPO_DIRECTORY = "downloaded_repos"

def parse_args():
    parser = argparse.ArgumentParser(
        description="""
            Takes in a directory name and retrieves all commits i
            and json files of github commits in the repositories. 
            Then, for each commit, grab the parent commit.
        """
    )

    parser.add_argument(
        "-d",
        "--directory",
        action="store",
        required=False,
        default='../../github_data/raw_commits',
        help="The directory containing json data of github commits."
    )

    parser.add_argument(
        "-n",
        "--no-download",
        action="store_true",
        required=False,
        help="This flag makes it so that you don't download the repositories and instead analyze based off of what you have."
    )
    
    return parser.parse_args()

def download_repo(repo_name: str):
    if "webkit" in repo_name.lower():
        logger.info(f"Repo '{repo_name}' is a webkit")
        return -1
    git_url = "https://github.com/" + repo_name + ".git"
    logger.info(f"Downloading repo '{git_url}'")
    with cwd(DOWNLOADED_REPO_DIRECTORY):
        try:
            subprocess.run(["git", "clone", git_url, repo_name], capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            logger.info(f"Repo {repo_name} download took too long")
            return -1
    return 1

def get_parent_commit(commit: str, repo_name: str) -> str:
    logger.info(f"Getting the parent commit for '{commit}'")
    path_to_repo = DOWNLOADED_REPO_DIRECTORY + '/' + repo_name
    if not os.path.exists(path_to_repo):
        logger.info(f"Path {path_to_repo} doesn't exist.")
        return "Parent commit retriever returned error."
    with cwd(path_to_repo):
        p = subprocess.run(["git", "log", "--pretty=%P", "-n", "1", commit], capture_output=True)
        if p.returncode != 0:
            return "Parent commit retriever returned error."

        parent_commit = p.stdout.decode('utf-8')
        return parent_commit.strip('\n')

def get_commit_message(file_name: str) -> str:
    with open(file_name, 'r') as f:
        data = json.load(f)
    return data["commit"]["message"]

def get_repo_name(file_name: str) -> str:
    dirs = file_name.split('/')
    return (dirs[-3]+ '/' + dirs[-2])

def get_commit_name(file_name: str) -> str:
    dirs = file_name.split('/')
    return (dirs[-1].replace('.json', ''))

def main() -> None:
    args = parse_args()
    list_of_rows = []
    list_of_files = []
    # get all file names
    for dirpath, subdirs, files in os.walk(args.directory):
        for file in files:
            file = os.path.join(dirpath, file)
            list_of_files.append(file)

    # download every repository.
    if not args.no_download:
        for file in list_of_files:
            download_repo(get_repo_name(file))

    # get the parent commit of each repository.
    for file in list_of_files:
        parent_commit = get_parent_commit(get_commit_name(file), get_repo_name(file))
        commit_message = get_commit_message(file)
        if not parent_commit == "Parent commit retriever returned error.":
            list_of_rows.append([get_repo_name(file), get_commit_name(file), [parent_commit], commit_message])

    # make a table.
    df = pd.DataFrame(list_of_rows, columns=["repository", "commit", "parent", "message"])
    # convert to json.
    table_to_json = df.to_json(orient="split")
    parsed = json.loads(table_to_json)
    with open("github_data.json", 'w') as f:
        json.dump(parsed, f, indent=4)

if __name__ == "__main__":
    main()