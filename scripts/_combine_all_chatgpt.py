import joblib
import pandas as pd
import csv
import numpy as np

from common import (
    cleanup_files,
    convert_dtypes,
    force_refresh,
    get_logger,
    get_path,
    import_chatgpt_events,
    initialize,
    import_chatgpt_dataset,
)

initialize()

data = pd.DataFrame()

def export_events(data):
    pd.DataFrame(data).sort_values(["project", "pull_number"]).to_csv(
        get_path("all_chatgpt_events"), index=False, quoting=csv.QUOTE_ALL, escapechar="\\"
    )

def combine_projects(project):
    logger = get_logger(__file__)
    logger.info(f"{project}: Concatenating ChatGPT events")
    chatgpt_events = import_chatgpt_events(project)
    chatgpt_events = chatgpt_events.reset_index()
    chatgpt_events['project'] = project
    return chatgpt_events


def main():
    file_path = "../../../data/data_collection/pull_filename_contains_chatgpt.csv"
    prs = pd.read_csv(file_path)
    prs = prs[(prs['filename_contains_chatgpt'] == False)]

    projects = []
    pr_by_repo = prs.groupby("project")["pr_number"].apply(list).to_dict()

    for project, pr_numbers in pr_by_repo.items():
        projects.append(project)
    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            results = parallel(joblib.delayed(combine_projects)(project) for project in projects)

        try:
            dfs = [result for result in results if isinstance(result, pd.DataFrame)]
            data = pd.concat(dfs)
            export_events(data)
        except Exception as e:
            print(f'Error during concatenation: {e}')


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop processing data")
        exit(1)
