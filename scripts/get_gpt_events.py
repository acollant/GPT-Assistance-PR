import joblib
import numpy as np
import pandas as pd
import csv
from collections import Counter
# from googletrans import Translator
# from langdetect import detect_langs, LangDetectException
import os

from common import (
    cleanup_files,
    convert_dtypes,
    force_refresh,
    get_logger,
    get_path,
    import_timelines,
    initialize,
    import_bots,
    import_chatgpt_events,
    is_chatgpt_event,
)

ngram_counter = Counter()

initialize()

# def translate_to_english(text):
#     if text is None or pd.isna(text) or text == '<NA>':
#         return ''
#     try:
#         probabilities = detect_langs(text)
#         if any(lang.lang == 'en' and lang.prob >= 90 for lang in probabilities):
#             return text
#         translator = Translator()
#         translation = translator.translate(text, dest='en')
#         return translation.text
#     except LangDetectException:
#         try:
#             translator = Translator()
#             translation = translator.translate(text, dest='en')
#             return translation.text
#         except Exception as e:
#             print(f"Failed to translate text after detection failure: {e}")
#             return text
#     except Exception as e:
#         print(f"Failed to translate text: {e}")
#         return text
    
# @convert_dtypes
def get_chatgpt_events(timelines, bots):
    if timelines['body'].dtype != object: 
        timelines['body'] = timelines['body'].astype(str)
    # timelines['body'] = timelines['body'].apply(lambda x: translate_to_english(x))
    if timelines['title'].dtype != object: 
        timelines['title'] = timelines['title'].astype(str)
    # timelines['title'] = timelines['title'].apply(lambda x: translate_to_english(x))
    human_events = timelines.query("~is_bot")
    chatgpt_events = human_events.query("body.str.contains('gpt', case=False) or title.str.contains('gpt', case=False)", engine="python")
    # chatgpt_events['combined'] = chatgpt_events['title'] + " " + chatgpt_events['body']
    # chatgpt_events['chatgpt_response'] = chatgpt_events['combined'].apply(lambda x: query_gpt_turbo(x))
    # chatgpt_events['is_chatgpt'] = chatgpt_events['chatgpt_response'].apply(lambda x: is_chatgpt_event(x))
    # chatgpt_events.drop(columns=['combined'], inplace=True)
    # chatgpt_events['2-gram'] = chatgpt_events.apply(lambda x: ', '.join(chatgpt_ngrams(str(x['title']) + " " + str(x['body']), 2)), axis=1)
    # chatgpt_events['3-gram'] = chatgpt_events.apply(lambda x: ', '.join(chatgpt_ngrams(str(x['title']) + " " + str(x['body']), 3)), axis=1)
    # local_ngram_counter = Counter()
    # chatgpt_events.apply(lambda x: local_ngram_counter.update(chatgpt_ngrams((str(x['title']) + " " + str(x['body'])).lower(), 2)), axis=1)
    # chatgpt_events.apply(lambda x: local_ngram_counter.update(chatgpt_ngrams((str(x['title']) + " " + str(x['body'])).lower(), 3)), axis=1)
    chatgpt_events = chatgpt_events.reset_index()
    chatgpt_events['is_first'] = chatgpt_events.groupby('pull_number')['event_number'].transform(min) == chatgpt_events['event_number']
    chatgpt_events = chatgpt_events.set_index(['pull_number', 'event_number'])
    timelines['is_chatgpt'] = timelines.index.isin(chatgpt_events.index)
    timelines['is_first_chatgpt'] = timelines['is_chatgpt'] & chatgpt_events['is_first']
    return timelines, chatgpt_events

@convert_dtypes
def retry_openai_call(chatgpt_events):
    retry_mask = chatgpt_events['chatgpt_response'] == 'Retry'
    if retry_mask.any():
        chatgpt_events.loc[retry_mask, 'combined'] = chatgpt_events.loc[retry_mask, 'title'] + " " + chatgpt_events.loc[retry_mask, 'body']
        chatgpt_events.loc[retry_mask, 'chatgpt_response'] = chatgpt_events.loc[retry_mask, 'combined'].apply(query_gpt_turbo)
        chatgpt_events.loc[retry_mask, 'is_chatgpt'] = chatgpt_events.loc[retry_mask, 'chatgpt_response'].apply(is_chatgpt_event)
        chatgpt_events.drop(columns=['combined'], inplace=True)
    return chatgpt_events

@convert_dtypes
def chatgpt_proceeding_events(timelines):
    timelines['is_proceeding_chatgpt'] = False
    timelines['chatgpt_event'] = ''

    for idx, row in timelines.iterrows():
        if row['is_chatgpt']:
            current_pull, current_event = idx
            chatgpt_event_no = current_event
            next_event_index = (current_pull, current_event + 1)
            while next_event_index in timelines.index:
                next_event = timelines.loc[next_event_index]
                if next_event['actor'] != row['actor'] and next_event['actor'] != 'ghost' and not next_event['is_bot']:
                    timelines.at[next_event_index, 'is_proceeding_chatgpt'] = True
                    timelines.at[next_event_index, 'chatgpt_event'] = str(chatgpt_event_no)
                    break
                current_event += 1
                next_event_index = (current_pull, current_event + 1)
    return timelines

@convert_dtypes
def add_bot(timelines, bots, owners):
    timelines["is_bot"] = (
        timelines["actor"].str.endswith(("bot", "[bot]"))
        | timelines["actor"].isin(bots)
        | timelines["actor"].isin(owners)
    )
    return timelines

def export_dataset(project, chatgpt_events, path_key):
    chatgpt_events.to_csv(get_path(path_key, project), quoting=csv.QUOTE_ALL, escapechar="\\")

def export_timelines(project, timelines):
    timelines = timelines.reset_index()
    pd.DataFrame(timelines).sort_values(["pull_number", "event_number"]).to_csv(
        get_path("timelines", project), index=False, quoting=csv.QUOTE_ALL, escapechar="\\"
    )


def get_events(project, bots, owners):
    logger = get_logger(__file__)
    logger.info(f"{project}: Processing ChatGPT events")
    timelines = import_timelines(project)
    timelines = add_bot(timelines, bots, owners)
    # chatgpt_events = get_chatgpt_events(timelines, bots)
    timelines, chatgpt_events = get_chatgpt_events(timelines, bots)
    timelines = chatgpt_proceeding_events(timelines)
    export_dataset(project, chatgpt_events, 'chatgpt_events')
    # export_dataset(project, chatgpt_events, 'heuristic_chatgpt_events')
    export_timelines(project, timelines)
    # export_dataset(project, chatgpt_proceding_events, 'chatgpt_proceeding_events')
    # return local_ngram_counter

def retry_failed_events(project, bots):
    logger = get_logger(__file__)
    logger.info(f"{project}: Retrying ChatGPT events")
    chatgpt_events = import_chatgpt_events(project)
    chatgpt_events = retry_openai_call(chatgpt_events)
    export_dataset(project, chatgpt_events, 'chatgpt_events')

def export_ngrams():
    """Exports the collected n-grams and their frequencies to a CSV file."""
    with open(get_path("ngram_frequencies"), 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["n-gram", "Frequency"])
        for ngram, freq in ngram_counter.items():
            writer.writerow([ngram, freq])

def main():
    file_path = get_path('gpt_filtered_pulls')#+"/data/repository_with_gpt_pr.csv"
    prs = pd.read_csv(file_path)
    
    projects = []

    pr_by_repo = prs.groupby("repo_name")["PR Number"].apply(list).to_dict()
    
    for project, pr_numbers in pr_by_repo.items():
        if cleanup_files("chatgpt_events", force_refresh(), project):
            projects.append(project)
        else:
            print(f"Skip processing data for project {project}")
    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            parallel(
                joblib.delayed(get_events)(project, bots=import_bots().index, owners=[project.split("/")[0] for project in projects]) for project in projects)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop processing data")
        exit(1)

