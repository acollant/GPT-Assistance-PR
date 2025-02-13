#source llm-pr/bin/activate 
from __future__ import unicode_literals
import re

import os
import joblib
import pandas as pd
import csv
import pathlib

from collections import Counter
from urllib.parse import urlparse
import yarl
import math
import numpy
import json

import scipy.stats as stats

import plotly.express as px

import matplotlib.pyplot as plt
import numpy as np
from enum import Enum
from numpy.linalg import norm
#
#from scipy.stats import spearmanr

from common import (
    cleanup_files,
    force_refresh,
    get_logger,
    get_path,
    initialize,
    selected,
    preprocessed,
    processed,
    toanalyze,
    import_timelines,
    import_project_timelines,
    chatgpt_ngrams,
    import_project_pulls,
    import_dataset,
    open_metadata,
    count_months,
    import_events_gpt,
    import_project_timelines_gpt,
    count_hours,
    open_commits,
    import_factors,
    initialize_all,
    
)
columns_=["project","pull_number","event_number","event","actor","time","state","commit_id",
        "referenced","sha","title","html_url","is_bot","is_chatgpt","is_first_chatgpt",
        "is_proceeding_chatgpt","chatgpt_event"]

columns_review=["project","pull_number","event_number_pull","event_pull","actor_pull",
              "time_pull","state_pull","is_bot_pull","is_chatgpt_pull",
              "event_number_review","event_review","actor_review",
              "time_review","state_review","is_bot_review","is_chatgpt_review","project_age_month"]
    
columns_submission_RQ1 = ["project","pull_number","event_number_submission","event_submission","actor_submission","time_submission",
                        "state_submission","is_bot_submission","is_chatgpt_submission","is_chatgpt_for_submission","commit_submission",
                        "time_to_merge_h","project_age_month","no_commits","PR_size(SLOC)","no_changed_files","is_gpt"]

columns_submission_RQ2 = ["project","pull_number","actor","merged_or_not","project_age_month","no_commits","PR_size(SLOC)","no_changed_files","is_gpt"]

column_resolution_RQ1 =  ["project","pull_number","actor","project_age_month","no_commits","PR_size(SLOC)","no_changed_files","time_to_merge_h"]
    

summary_data= {
            'project': [],
            'pull_number':[],
            'actor':[],
            'event': [],
            'time': [],
            'phase':[]
        }

pr_phases = {
    'event_0': 'submission time',
    'event_1': "review time",
    'event_2': 'change time',
    'event_3': 'resolution time',
}


class PHASE(Enum):
        at_submission = 1
        at_review = 2
        at_waiting_before_change = 3
        at_change = 4
        at_waiting_after_acceptance = 5
        at_resolution = 6
    
ngram_counter = Counter()#new
initialize()
#initialize_all()
logger = get_logger(__file__, modules={"urllib3": "ERROR"})
def get_project():
    directory = get_path("data")
    file_ = pathlib.Path(__file__).parent / directory / "projects.csv"
    projects = []
    n = 0
   
    #logger.info(f"projects:  {projects}")
    with open(file_, newline='') as f:
        f.readline()
        for line in f.readlines():
            #if n > 0:
            #projects.append(line.strip().lower())
            projects.append(line.split(",")[0].strip())
            #n=+1 
    #logger.info(f"projects:  {projects}")
    #input()
    return projects


def is_merged(project, pull_number):
    query_ = 'pull_number == ' + str(pull_number)
    timelines = import_project_timelines(project).query(query_)
    
    return (len(timelines.query("event == 'merged'")) > 0)
            
   

  
def get_factors(project, pull_number):

    query_ = f"pull_number == {str(pull_number)}"
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: factors")
    columns_=["project","pull_number","no_commits","PR_size","no_changed_files"]
   
    factors = import_factors(project).query(query_)
    
    
    summary = factors.groupby('pull_number').agg(
        no_commits =('sha', 'count'),
        added_lines =('added_lines', 'sum') ,
        deleted_lines = ('deleted_lines', 'sum'),
        no_changed_files =('changed_files', 'sum')
    ).reset_index()
    
    summary['PR_size(SLOC)'] = summary['added_lines'] + summary['deleted_lines']
    summary['project'] = project
    summary = summary.drop(columns=['added_lines','deleted_lines'])
    
    return summary

def process_resolution_time(project, pull_number):
    columns_ = ["project","pull_number",
              "event_number_pull","event_pull","actor_pull","time_pull","state_pull","is_bot_pull","is_chatgpt_pull",
              "event_number_review","event_review","actor_review", "time_review","state_review","is_bot_review","is_chatgpt_review",
              "project_age_month","no_commits","PR_size","no_changed_files"]

    query_ = 'pull_number == ' + str(pull_number)
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: process_resolution_time")

    
    timelines =  import_project_timelines_gpt(project).query(query_)[["pull_number",
              "event_number","event_x","actor","time","state","is_bot","is_chatgpt","is_gpt_for"]]
    timelines['project'] = project
    
    #timelines['event_number'] = timelines['event_number'].astype(int)
    timeline_pulled = timelines.query("event_x == 'pulled'")

    timeline_first_review = timelines.query("event_x == 'merged'").tail(1)
   
    timeline_pulled = timeline_pulled.reset_index()
    timeline_pulled = timeline_pulled.drop(['index'], axis=1)
    timeline_first_review = timeline_first_review.reset_index()
    timeline_first_review = timeline_first_review.drop(['index'], axis=1)
    
    gpt_in_phase_number = 0
    if len(timeline_first_review["event_number"]) > 0 :
       #print('pull_event_number: ',timeline_pulled["event_number"][0])
       #print('timeline_first_review:', timeline_first_review["event_number"][0])
       pull_event_number_ = str(timeline_pulled["event_number"][0])
       timeline_first_review_ = str(timeline_first_review["event_number"][0])
       query_ = "is_gpt_for == 'gpt assistance' and event_number >=" + pull_event_number_ + " and event_number <= " + timeline_first_review_
       #print(query_)          
       in_phase_list = timelines.query(query_)
       gpt_in_phase_number = len(in_phase_list)
       
       #print(timeline_pulled["time"])
       #print(timeline_first_review["time"])

       pushed_date = pd.Timestamp(timeline_first_review["time"][0]).tz_localize(None) #print(pd.to_datetime(timeline_first_review["time"][0]).tz_localize(None))
    pulled_date = pd.Timestamp(timeline_pulled["time"][0]).tz_localize(None)#pd.to_datetime(timeline_pulled["time"][0]).tz_localize(None)
          
    
    df_review_ = pd.DataFrame()#(columns=columns_)
    df_review_ = pd.DataFrame()
    df_review_["project"] = timeline_pulled['project']
    df_review_["pull_number"] = timeline_pulled["pull_number"]
    df_review_["event_number_pull"] = timeline_pulled["event_number"]
    df_review_["event_pull"] = timeline_pulled["event_x"]
    df_review_["actor_pull"] = timeline_pulled["actor"]
    df_review_["time_pull"] = timeline_pulled["time"]
    df_review_["state_pull"] = timeline_pulled["state"]
    df_review_["is_bot_pull"] = timeline_pulled["is_bot"]
    df_review_["is_chatgpt_pull"] = timeline_pulled["is_chatgpt"]
    df_review_["is_chatgpt_for_pull"] = timeline_pulled["is_gpt_for"]
    #df_review_["project_review"] = timeline_first_review['project']
    #df_review_["pull_number_review"] = timeline_first_review["pull_number"]
    df_review_["event_number_review"] = timeline_first_review["event_number"]
    df_review_["event_review"] = timeline_first_review["event_x"]
    df_review_["actor_review"] = timeline_first_review["actor"]
    df_review_["time_review"] = timeline_first_review["time"]
    df_review_["state_review"] = timeline_first_review["state"]
    df_review_["is_bot_review"] = timeline_first_review["is_bot"]
    df_review_["is_chatgpt_review"] = timeline_first_review["is_chatgpt"]
    df_review_["number_gpt_mention"] = gpt_in_phase_number
    df_review_["is_chatgpt_for_review"] = timeline_first_review["is_gpt_for"]


    df_review_["time_to_merge_h"] = count_hours( pulled_date,pushed_date)
    project_create_at = get_creation_dt_project(project, pull_number)
    df_review_["project_age_month"] = count_months(project_create_at,pulled_date) #get_creation_dt_project(project, pull_number)
    
    factors =  get_factors(project, pull_number)

    df_review_["no_commits"] = factors['no_commits']
    df_review_["PR_size(SLOC)"] = factors['PR_size(SLOC)']
    df_review_["no_changed_files"] = factors['no_changed_files']
    df_review_["actor"] = df_review_["actor_review"]
   
    df_review_ = df_review_[["project","pull_number","actor",
                             "project_age_month","no_commits","PR_size(SLOC)","no_changed_files","time_to_merge_h"]]
    #print (df_review_)
    #input("stop resolution")
    return df_review_

def get_creation_dt_project(project, pull_number):
    print("project:", project, "pull number:", pull_number)
    query_ = 'pull_number == ' + str(pull_number)
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: get_creation_dt_project data")
    dataset = import_dataset(project).query(query_)
    metadata = open_metadata(project)
    #pulled = dataset.query("event == 'pulled'")
    project_created_at = pd.Timestamp(metadata["created_at"]).tz_localize(None)
    
    return project_created_at



def export_resolution_time(phase):
    pd.DataFrame(phase).to_csv(get_path("at_resolution_time"), index=False)


def main():
    projects = []
    gpt_pulls = import_project_pulls().sort_values(by='owner_login')
    df_resolution = pd.DataFrame(columns=column_resolution_RQ1)
    
    for _, row in gpt_pulls.iterrows():
        project = row['owner_login'] + '_' + row['name']
        pull_number = row['number']
        is_gpt = row['is_gpt']
        if is_merged(project, pull_number) == True: 
            df_ = process_resolution_time(project, pull_number)
            df_["is_gpt"] = is_gpt
            df_resolution = df_resolution._append(df_, ignore_index = True) 
    
    #df_resolution = df_resolution._append(process_resolution_time(project, pull_number), ignore_index = True)
    export_resolution_time(df_resolution)


    

if __name__ == "__main__":
    try:
       main()
      

    except KeyboardInterrupt:
        print("Stop processing phase")
        exit(1)


