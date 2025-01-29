import joblib
import pandas as pd
import csv
import os
import pathlib
from common import (
    initialize,
    convert_dtypes,
    get_logger,
    get_path,
    import_chatgpt_events,
    query_gpt_turbo,
    is_chatgpt_event,
    filename_contains_chatgpt,
)

initialize()
    
def import_all_chatgpt_events():
    return pd.read_csv(get_path("all_chatgpt"))

@convert_dtypes
def select_project_events(project, chatgpt_events):
    project_events = chatgpt_events[chatgpt_events['project'] == project]
    project_events = project_events.drop(columns=['project'])
    return project_events

@convert_dtypes
def retry_openai_call(chatgpt_events):
    # retry_mask = chatgpt_events['chatgpt_response'] == 'Retry'
    retry_mask = chatgpt_events['chatgpt_response'].isnull()
    if retry_mask.any():
        if chatgpt_events['body'].dtype != object:
            chatgpt_events['body'] = chatgpt_events['body'].astype(str)
        if chatgpt_events['title'].dtype != object:
            chatgpt_events['title'] = chatgpt_events['title'].astype(str)
        chatgpt_events['combined'] = chatgpt_events['title'] + " " + chatgpt_events['body']
        chatgpt_events['chatgpt_response'] = chatgpt_events['combined'].apply(lambda x: query_gpt_turbo(x))
        chatgpt_events['is_chatgpt'] = chatgpt_events['chatgpt_response'].apply(lambda x: is_chatgpt_event(x))
        chatgpt_events.drop(columns=['combined'], inplace=True)
    
    return chatgpt_events

def bool_ischatgpt(chatgpt_events):
    chatgpt_events['is_chatgpt'] = chatgpt_events['chatgpt_response'].apply(lambda x: is_chatgpt_event(str(x)))
    return chatgpt_events

def export_dataset(project, chatgpt_events, path_key):
    chatgpt_events.to_csv(get_path(path_key, project), quoting=csv.QUOTE_ALL, escapechar="\\")

def get_events(project):
    logger = get_logger(__file__)
    logger.info(f"{project}: Selecting ChatGPT events")
    all_chatgpt_events = import_all_chatgpt_events()
    project_events = select_project_events(project, all_chatgpt_events)
    export_dataset(project, project_events, 'chatgpt_events')

def retry_failed_events(project):
    logger = get_logger(__file__)
    logger.info(f"{project}: Retrying ChatGPT events")
    chatgpt_events = import_chatgpt_events(project)
    chatgpt_events = retry_openai_call(chatgpt_events)
    export_dataset(project, chatgpt_events, 'chatgpt_events')

def assign_bool_ischatgpt(project):
    logger = get_logger(__file__)
    logger.info(f"{project}: Assigning bool ChatGPT events")
    chatgpt_events = import_chatgpt_events(project)
    
    chatgpt_events = bool_ischatgpt(chatgpt_events)
    
    if 'Unnamed: 0' in chatgpt_events.columns:
        chatgpt_events = chatgpt_events.drop(columns=['Unnamed: 0'])
    export_dataset(project, chatgpt_events, 'chatgpt_events')

def pr_chatgpt_files(project, pr_numbers):
    logger = get_logger(__file__)
    logger.info(f"{project}: Checking PR ChatGPT files")
    chatgpt_events = import_chatgpt_events(project)
    if filename_contains_chatgpt(project):
        chatgpt_events = bool_ischatgpt(chatgpt_events)
        if 'Unnamed: 0' in chatgpt_events.columns:
            chatgpt_events = chatgpt_events.drop(columns=['Unnamed: 0'])
        export_dataset(project, chatgpt_events, 'chatgpt_events')
    else:
        print(f"{project}: No ChatGPT files found")

def main():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("gpt_filtered_pulls.csv")
    prs = pd.read_csv(file_path)
    
    
    projects = []
    
    pr_by_repo = prs.groupby("repo_name")["PR Number"].apply(list).to_dict()

    for project, pr_numbers in pr_by_repo.items():
        projects.append(project)

    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            parallel(
                joblib.delayed(assign_bool_ischatgpt)(project) for project in projects)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop processing data")
        exit(1)