import joblib
import pandas as pd
import csv
import os
import requests
import pathlib

from common import (
    initialize,
    get_logger,
    open_patches_raw,
    filename_contains_chatgpt,
)

initialize()

def get_pr_patches(pr_number, patch):
    logger = get_logger(__file__)
    logger.info(f"Analyzing patch for pull request {pr_number}")
    contains_chatgpt = filename_contains_chatgpt(patch)
    return contains_chatgpt

def pr_chatgpt_files(project):
    logger = get_logger(__file__)
    logger.info(f"{project}: Checking PR ChatGPT files")
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("gpt_filename_contains_chatgpt.csv")
    patches = open_patches_raw(project)
    for pr_number, patch in patches.items():
        filename_contains_chatgpt = get_pr_patches(pr_number, patch)
        pull_url = f"https://github.com/{project}/pull/{pr_number}"
        patch_url = f"https://patch-diff.githubusercontent.com/raw/{project}/pull/{pr_number}.patch"
        # if not contains_chatgpt:
        with open(file_path, "a") as f:
            writer = csv.writer(f)
            writer.writerow([project, pr_number, pull_url, patch_url, filename_contains_chatgpt])
    

def main():
    logger = get_logger(__file__)
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("gpt_filtered_pulls.csv")
    
    prs = pd.read_csv(file_path)
    
   

    projects = []
    
    pr_by_repo = prs.groupby("repo_name")["PR Number"].apply(list).to_dict()

    chatgpt_project_names = []

    for project, pr_numbers in pr_by_repo.items():
        projects.append(project)
    
    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            parallel(
                joblib.delayed(pr_chatgpt_files)(project) for project in projects)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop processing data")
        exit(1)