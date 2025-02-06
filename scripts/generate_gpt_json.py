import joblib
import numpy as np
import pandas as pd
import csv
from collections import Counter
import os
import json
import pathlib

from common import (
    convert_dtypes,
    get_logger,
    get_path,
    import_timelines,
    import_pulls,
    initialize,
    import_bots,
)

initialize()

df = pd.DataFrame()

@convert_dtypes
def get_chatgpt_events(timelines, bots):
    if timelines['body'].dtype != object: 
        timelines['body'] = timelines['body'].astype(str)
    if timelines['title'].dtype != object: 
        timelines['title'] = timelines['title'].astype(str)
    # human_events = timelines.query("~is_bot")
    chatgpt_events = timelines.query("body.str.contains('gpt', case=False) or title.str.contains('gpt', case=False)", engine="python")
    chatgpt_events = chatgpt_events.reset_index()
    chatgpt_events['is_first'] = chatgpt_events.groupby('pull_number')['event_number'].transform(min) == chatgpt_events['event_number']
    chatgpt_events = chatgpt_events.set_index(['pull_number', 'event_number'])
    timelines['is_chatgpt'] = timelines.index.isin(chatgpt_events.index)
    timelines['is_first_chatgpt'] = timelines['is_chatgpt'] & chatgpt_events['is_first']
    return timelines

def sample_data(project, pr_numbers, bots):
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: Sampling data")
    
    timelines = import_timelines(project)
    pulls = import_pulls(project)
    pulls = pulls.query("number == @pr_numbers")
    
    try:
        timelines = timelines[timelines['is_chatgpt']==True]
        #timelines = timelines.query("is_chatgpt=='True'")
        # ChatGPT pull are pulls with events in timelines, add the event and event html url to the pull
        if not timelines.empty:
            timelines = timelines.reset_index()
            timelines = timelines[["pull_number", "event_number", "event", "title", "body", "actor", "html_url", "time"]].drop_duplicates()
            chatgpt_pulls = pulls.merge(timelines, how="left", left_index=True, right_on="pull_number")
            chatgpt_pulls.reset_index(inplace=True)
            chatgpt_pulls["project"] = project
            output = chatgpt_pulls[["project", "pull_number", "html_url_x", "title_x", "event", "html_url_y", "actor", "title_y", "body_y", "time"]]
            output = output.rename(columns={
                "html_url_x": "url",
                "html_url_y": "event_url",
                "title_x": "pr_title",
                "title_y": "event_title",
                "body_y": "body"
            })
        else:
            chatgpt_pulls = pulls.merge(timelines, how="left", left_index=True, right_on="pull_number")
            chatgpt_pulls.reset_index(inplace=True)
            chatgpt_pulls["project"] = project
            output = chatgpt_pulls[["project", "pull_number", "html_url_x", "title_x", "event", "html_url_y", "actor", "title_y", "body_y", "time"]]
            output = output.rename(columns={
                "title_x": "pr_title",
                "html_url_x": "url",
                "html_url_y": "event_url",
                "title_y": "event_title",
                "body_y": "body"
            })
    except Exception as error:
        print('err:', error, project)
        output =pd.DataFrame()

    return output

def convert_to_json(data):
    json_data = []
    data = data.fillna('')
    grouped = data.groupby(['url', 'project', 'pull_number'])
    for (url, project, pr_number), group in grouped:
        pr_data = {
            "url": url,
            "project": project,
            "pr_number": int(pr_number),
            "pr_title": group["pr_title"].values[0],
            "GPTMention": [
                {
                    "event": row["event"],
                    "url": row["event_url"],
                    "actor": row["actor"],
                    "title": row["event_title"],
                    "body": row["body"],
                    "created_at": str(row["time"])
                }
                for idx, row in group.iterrows()
            ]
        }
        json_data.append(pr_data)
    return json_data

def export_datasets(data):
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    data = data.sample(frac=1, random_state=42)
    print(f"Total number of sampled pull requests: {len(data)}")
    pd.DataFrame(data).sort_values(["project", "pull_number"]).to_csv(
        directory / get_path("gpt_pull_requests"), index=False, quoting=csv.QUOTE_ALL, escapechar="\\"
    )

def export_json_datasets(data):
    json_data = convert_to_json(data)
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    with open(directory / get_path("gpt_pull_requests_json"), 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

def main():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("gpt_filename_contains_chatgpt.csv")
    prs = pd.read_csv(file_path)
    print(f"Total number of pull requests: {len(prs)}")

    projects = []

    pr_by_repo = prs.groupby("project")["pr_number"].apply(list).to_dict()

    
    for project, pr_numbers in pr_by_repo.items():
        projects.append(project)

    

    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            data = parallel(joblib.delayed(sample_data)(project, pr_by_repo[project], bots=import_bots().index) for project in projects)
            df = pd.concat(data)

    export_datasets(df)
    export_json_datasets(df)
            

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop processing data")
        exit(1)