import json
import pandas as pd
import joblib
import re
import pathlib

from common import (
    initialize,
    get_logger,
    open_patches_raw
)

initialize()

def export_data(data):
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    file_path = directory / pathlib.Path("gpt_pull_requests_filenames.json")
    try:
        with open(file_path, 'r+', encoding='utf-8') as file:
            file_data = json.load(file)  
            file_data.extend(data)     
            file.seek(0)               
            json.dump(file_data, file, ensure_ascii=False, indent=4)
            file.truncate()          
    except FileNotFoundError:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)


def get_modified_files(patch_text):
    lines = patch_text.splitlines()
    modified_files = []
    for line in lines:
        if line.startswith("--- ") or line.startswith("+++ "):
            filename = line[4:].strip()
            if filename != "/dev/null":
                filename = re.sub(r"^[ab]/", "", filename)
                if filename not in modified_files:
                    modified_files.append(filename)
    return modified_files

def add_pr_patch_to_json(project, pr_numbers, pull_json):
    logger = get_logger(__file__)
    logger.info(f"{project}: Checking PR ChatGPT files")
    patches = open_patches_raw(project)
    for pr_number, patch in patches.items():
        if int(pr_number) in pr_numbers:
            for pr in pull_json:
                if pr["pr_number"] == int(pr_number):
                    modified_files = get_modified_files(patch)
                    if "modified_files" not in pr:
                        pr["modified_files"] = []
                    pr["modified_files"].extend(modified_files)
                    logger.info(f"Added modified files of {pr_number} in project {project}")

    return pull_json

def main():
    logger = get_logger(__file__)
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    file_path = directory / pathlib.Path("gpt_pull_requests.json")
    
    with open(file_path, 'r') as file:
        pull_json = json.load(file)
    
    prs = pd.DataFrame(pull_json)

    projects = []
    
    pr_by_repo = prs.groupby("project")["pr_number"].apply(list).to_dict()

    
    for project, pr_numbers in pr_by_repo.items():
        projects.append(project)

    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            data = parallel(joblib.delayed(add_pr_patch_to_json)(project, pr_by_repo[project], [pr for pr in pull_json if pr['project'] == project]) for project in projects)
            export_data(data)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop joining patches to json data")
        exit(1)
