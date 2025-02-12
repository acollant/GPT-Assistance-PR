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

import numpy as np
from enum import Enum
from numpy.linalg import norm

from common import (
    get_logger,
    import_project_pulls,
    import_dataset,
    open_metadata,
    count_months,
    import_project_timelines_gpt,
    count_hours,
    import_factors,
    initialize,
    get_path,
)
initialize()

class PHASE(Enum):
        at_submission = 1
        at_review = 2
        at_waiting_before_change = 3
        at_change = 4
        at_waiting_after_acceptance = 5
        at_resolution = 6

class ACTOR(Enum):
        CONTRIBUTOR = 1
        REVIEWER = 2
at_submission = {
        "states_from": ['committed'],
        "states_to": ['pulled'],
        "event": 0,
        "actor": ACTOR.CONTRIBUTOR
    }

at_review = {
        "states_from": ['pulled'],
        "states_to": ['reviewed', 'commented', 'line-commented', 'commit-commented', 'reviewed-commented', 'review-commented'],
        "event": 0,
        "actor": ACTOR.REVIEWER
    }
  
at_waiting_before_change = {
        "states_from": ['reviewed', 'commented', 'line-commented', 'commit-commented', 'reviewed-commented', 'review-commented'],
        "states_to":   ['reviewed', 'commented', 'line-commented', 'commit-commented', 'reviewed-commented', 'review-commented'],
        "event": 0,
       # "actor": ACTOR.REVIEWER
    }

at_change = {
        "states_from": ['reviewed', 'commented', 'line-commented', 'commit-commented', 'reviewed-commented', 'review-commented'],
        "states_to": ['reviewed','committed', 'head_ref_force_pushed', 'review-commented','line-commented', 'commit-commented', 'reviewed-commented', 'review-commented'],
        "states_end": ['merged','closed'],
        "event": 0,
        "actor": ACTOR.REVIEWER
    }
    
at_waiting_after_acceptance ={
        "states_from": ['reviewed','committed', 'head_ref_force_pushed', 'review-commented','line-commented', 'commit-commented', 'reviewed-commented', 'review-commented'],
        "states_to": ['merged', 'closed'],
        "event": 0,
    }

at_resolution = {
        "states_from": ['pulled'],
        "states_to": ['merged', 'closed'],
    }

def reset_dataframe(df):
    df = df.reset_index()
    df = df.drop(['index'], axis=1)
    return df

def get_factors_by_sha(project, pull_number, sha):
    query_ = f"pull_number == {str(pull_number)} and sha in {sha}"  
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"Get factor by sha: {project}: and pull: {pull_number} and sha list: {sha}")
    columns_=["project","pull_number","no_commits","PR_size","no_changed_files"]
   
    factors = import_factors(project).query(query_)
    
    
    summary = factors.groupby('pull_number').agg(
        no_commits =('sha', 'count'),
        added_lines =('added_lines', 'sum') ,
        deleted_lines = ('deleted_lines', 'sum'),
        no_changed_files =('changed_files', 'sum')
    ).reset_index()
    
    summary['PR_size'] = summary['added_lines'] + summary['deleted_lines']
    #summary['project'] = project
    summary = summary.drop(columns=['added_lines','deleted_lines','pull_number'])
    
    return summary


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

def postprocess_data(project, pull_number):
    query_ = 'pull_number == ' + str(pull_number)
    print(query_)
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: Postprocessing data")
    dataset = import_dataset(project).query(query_)
    metadata = open_metadata(project)
    merged = dataset.query("event == 'merged'")
    pulled = dataset.query("event == 'pulled'")
    closed = dataset.query("event == 'closed'").tail(1)
    is_open = 0
    if len(closed) == 0 and len(merged) == 0 : is_open = 1
    #print(pd.Timestamp(metadata["created_at"]).tz_localize(None))
    return {
        "project": project,
        "pull_number": pull_number,
        "language": metadata["language"],
        "stars": metadata["watchers"],
        #"age": count_months(pd.Timestamp(metadata["created_at"]).tz_localize(None), pulled["time"].max()),
        "contributors": pulled["actor"].nunique(),
        "bots": dataset.query("is_bot")["actor"].nunique(),
        "bot contributors": pulled.query("is_bot")["actor"].nunique(),
        "pulls": len(pulled),
        "open":is_open,# len(pulled.query("is_open")),
        "closed": len(closed),#len(pulled.query("is_closed")),
        "merged": len(merged),
        "maintainer responded": len(pulled.query("maintainer_latency.notna()")),
        "contributor responded": len(pulled.query("contributor_latency.notna()")),
    }

def get_phases(project, pull_number, phase, timelines):

    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"PROCESS PHASES=>{PHASE(phase).name}  project:{project} and pull#:{pull_number}")
    
    timelines = timelines.replace({numpy.nan: None})
    timelines['project'] = project
    timelines = reset_dataframe(timelines)
    contributor = timelines["actor"][0]
    actor_type = ACTOR(1).name
    events = []
    shas = []
    gpt_assistance = 0
    duration = None
    date_to = numpy.nan
    date_from = numpy.nan
    
    if phase == PHASE.at_submission:
        query_ = " event_number == " + str(at_submission['event'])
        query_ = query_ + f" and event_x=='{at_submission['states_from'][0]}'    "
        df_from = timelines.query(query_)
        if df_from.empty: return None
        df_from = reset_dataframe(df_from)
        
        date_from = pd.Timestamp(df_from["time"][0]).tz_localize(None)
        query_ = f"event_x=='{at_submission['states_to'][0]}' "
        df_to = timelines.query(query_)
        df_to = reset_dataframe(df_to)
        
    elif phase == PHASE.at_review:
        actor_type = ACTOR(2).name
        query_ =  f" event_x=='{at_review['states_from'][0]}'    "
        df_from = timelines.query(query_)
        if df_from.empty: return None
        df_from = reset_dataframe(df_from)
        if df_from['event_number'][0] == 0: return None
        date_from = pd.Timestamp(df_from["time"][0]).tz_localize(None)
        query_ = f"event_number != '{str(at_review['event'])}' and actor != '{contributor}' and ("
        for e in at_review['states_to']:
            query_ = query_ + f"event_x=='{e}'" + "  or "
        query_ = query_ +  f"event_x=='{e}' )"
        
        df_to = timelines.query(query_).head(1)
        if df_to.empty: return None
        timelines_ = timelines.query(query_)
        bot =   timelines_.query(query_).head(1)["actor"].to_string(index=False)
        if "[bot]" in bot.strip():
            df_bot = timelines_.query(query_)
            if not df_bot[~df_bot['actor'].str.lower().str.endswith('[bot]')].empty:
                df_to = df_bot[~df_bot['actor'].str.lower().str.endswith('[bot]')].head(1)

        df_to = reset_dataframe(df_to)
        contributor = df_to["actor"][0]
     
    elif phase == PHASE.at_waiting_before_change:
        query_ = f"event_number != '{str(at_waiting_before_change['event'])}' and actor != '{contributor}' and ("
        for e in at_change['states_from']:
            query_ = query_ + f"event_x=='{e}'" + "  or "
        query_ = query_ +  f"event_x=='{e}' )"
        
        df_from = timelines.query(query_).head(1)
        df_from = reset_dataframe(df_from)
        if df_from.empty: return None
        date_from = pd.Timestamp(df_from["time"][0]).tz_localize(None)
        
        df_to = timelines.query(query_).tail(1)
        df_to = reset_dataframe(df_to)
        if df_to.empty: return None
        timelines_ = timelines.query(query_)
        bot =   timelines_.query(query_).head(1)["actor"].to_string(index=False)
        if "[bot]" in bot.strip():
            df_bot = timelines_.query(query_)
            if not df_bot[~df_bot['actor'].str.lower().str.endswith('[bot]')].empty:
                df_to = df_bot[~df_bot['actor'].str.lower().str.endswith('[bot]')].head(1)

        df_to = reset_dataframe(df_to)
        contributor = df_to["actor"][0]
    elif phase == PHASE.at_change:
        query_ = f"event_number != '{str(at_change['event'])}' and actor != '{contributor}' and ("
        for e in at_change['states_from']:
            query_ = query_ + f"event_x=='{e}'" + "  or "
        query_ = query_ +  f"event_x=='{e}' )"
        df_from = timelines.query(query_).tail(1)
        df_from = reset_dataframe(df_from)
        if df_from.empty: return None
        date_from = pd.Timestamp(df_from["time"][0]).tz_localize(None)
        query_ = f"event_number != '{str(at_change['event'])}'  and ("
        for e in at_change['states_to']:
            query_ = query_ + f"event_x=='{e}'" + "  or "
        query_ = query_ +  f"event_x=='{e}' )"
        df_to = timelines.query(query_).tail(1)
        df_to = reset_dataframe(df_to)
        if df_to.empty: return None
        contributor = df_to["actor"][0]
    elif phase == PHASE.at_waiting_after_acceptance:
        query_ = f"event_number != '{str(at_waiting_after_acceptance['event'])}'  and ("
        for e in at_change['states_from']:
            query_ = query_ + f"event_x=='{e}'" + "  or "
        query_ = query_ +  f"event_x=='{e}' )"
        df_from = timelines.query(query_).tail(1)
        df_from = reset_dataframe(df_from)
        if df_from.empty: return None
        date_from = pd.Timestamp(df_from["time"][0]).tz_localize(None)
        query_ = f"event_number != '{str(at_waiting_after_acceptance['event'])}'  and ("
        for e in at_change['states_to']:
            query_ = query_ + f"event_x=='{e}'" + "  or "
        query_ = query_ +  f"event_x=='{e}' )"
        df_to = timelines.query(query_).tail(1)
        df_to = reset_dataframe(df_to)
        
        if df_to.empty: return None    
        timelines_ = timelines.query(query_)
        bot =   timelines_.query(query_).head(1)["actor"].to_string(index=False)
        if "[bot]" in bot.strip():
            df_bot = timelines_.query(query_)
            if not df_bot[~df_bot['actor'].str.lower().str.endswith('[bot]')].empty:
                df_to = df_bot[~df_bot['actor'].str.lower().str.endswith('[bot]')].head(1)

        df_to = reset_dataframe(df_to)
        contributor = df_to["actor"][0]   
    elif phase == PHASE.at_resolution:
        query_ =  f" event_x=='{at_resolution['states_from'][0]}'"
        df_from = timelines.query(query_)
        if df_from.empty: return None
        df_from = reset_dataframe(df_from)
        
        if df_from['event_number'][0] == 0: return None
        date_from = pd.Timestamp(df_from["time"][0]).tz_localize(None)
        query_ = ""#f"event_number != '{str(at_resolution['event'])}'  and ("
        for e in at_resolution['states_to']:
            query_ = query_ + f"event_x=='{e}'" + "  or "
        query_ = query_ +  f"event_x=='{e}' "
        
        df_to = timelines.query(query_).tail(1)
        if df_to.empty: return None
        #timelines = timelines.query(query_)
        bot =   timelines.query(query_).head(1)["actor"].to_string(index=False)
        df_to = reset_dataframe(df_to)
        if contributor != df_to["actor"][0]:
            actor_type = ACTOR(2).name
            contributor = df_to["actor"][0]
    
    if not df_to.empty:
        date_to = pd.Timestamp(df_to["time"][0]).tz_localize(None)
        duration = abs(round(count_hours( date_from, date_to),3))
        project_create_at = get_creation_dt_project(project, pull_number)
        project_age = count_months(project_create_at, date_to)
        if phase == PHASE.at_submission:
            df_phase = timelines.query("event_number <" + str(df_to['event_number'][0]) )
        if phase == PHASE.at_review:
            df_phase = timelines.query(f"{str(df_from['event_number'][0])} <= event_number <=   {str(df_to['event_number'][0])}")
        if phase == PHASE.at_waiting_before_change:
            #df_phase = timelines.query(f"event_number >  {str(df_from['event_number'][0])} and event_number <  {str(df_to['event_number'][0])}")
            df_phase = timelines.query(f"{str(df_from['event_number'][0])} < event_number < {str(df_to['event_number'][0])}")
        if phase == PHASE.at_change:
            #df_phase = timelines.query(f"event_number >=  {str(df_from['event_number'][0])} and event_number <=  {str(df_to['event_number'][0])}")
            
            if df_from['event_number'][0] < df_to['event_number'][0]:
                df_phase = timelines.query(f"{str(df_from['event_number'][0])} <= event_number <= {str(df_to['event_number'][0])}")
            else:
                query_ = ''
                for e in at_change['states_end']:
                    query_ = query_ + f"event_x=='{e}'" + "  or "
                query_ = query_ +  f"event_x=='{e}' "
                df_to = timelines.query(query_).head(1)
                df_to = reset_dataframe(df_to)
                if df_to.empty: return None
                df_phase = timelines.query(f"{str(df_from['event_number'][0])} <= event_number < {str(df_to['event_number'][0])}")
        if phase == PHASE.at_waiting_after_acceptance:
            #df_phase = timelines.query(f"event_number >  {str(df_from['event_number'][0])} and event_number <  {str(df_to['event_number'][0])}")
            df_phase = timelines.query(f"{str(df_from['event_number'][0])} < event_number <= {str(df_to['event_number'][0])}")
        if phase == PHASE.at_resolution:
            #df_phase = timelines.query(f"event_number >=  {str(df_from['event_number'][0])} and event_number <=  {str(df_to['event_number'][0])}")
            df_phase = timelines.query(f"{str(df_from['event_number'][0])} <= event_number <= {str(df_to['event_number'][0])}")
        
        if df_phase.empty: return None
        print("phases:",df_phase)
        for _, e in df_phase.iterrows():
            if e['sha'] != None: shas.append(e['sha'])
            if e['html_url'] != None: events.append(e['html_url'])
            if e['is_gpt_for'] == 'gpt assistance': gpt_assistance = 1
       
        no_commits =  0
        no_changed_files = 0 
        PR_size = 0
         
        if len(shas) > 0:
            df_f = get_factors_by_sha(project, pull_number, shas)
            if not df_f.empty:
                df_f = reset_dataframe(df_f) 
                no_commits = df_f['no_commits'][0]
                no_changed_files = df_f['no_changed_files'][0]  
                PR_size = df_f['PR_size'][0]
        else:
            pass
           
       
       
        factors = {
            "no_commits": int(no_commits),
            "no_changed_files":int(no_changed_files), 
            "PR_size": int(PR_size),
            "project_age": project_age,
        }  

    
    phase = {
        "name": PHASE(phase).name,
        "actor": contributor,
        "actor_type": actor_type,
        "events": events,
        "commit_id": shas,
        "gpt_assistance": gpt_assistance,
        "duration": duration,
        "factors": factors
    }
    return phase

def main():
    project_list = []
    phases = {}
    indexes = {}
    index = 0
    i = 0
    
    projects = import_project_pulls().sort_values(['owner_login','name'])
    for _, row in projects.iterrows():#get_project():
        project = row['owner_login'] + '_' + row['name']
        pull_number = row['number']
        is_gpt_pr = row['is_gpt']
        
        query_ = 'pull_number == ' + str(pull_number)
        timelines =  import_project_timelines_gpt(project).query(query_)  
        
        
        post_data = postprocess_data(project, pull_number)
        print(post_data)
        status = None

        if post_data['merged'] > 0:
            status = 'merged'
        #    at_resolution = process_resolution_phase(project, pull_number,status) 
        elif post_data['closed'] > 0:
            status = 'closed'
        #    at_resolution = process_resolution_phase(project, pull_number,status)
        elif post_data['open'] > 0:
            status = 'open'
        #    at_resolution = None
        
        pulls = {}
        
        pulls[pull_number] = {
            "is_GPT_PR": is_gpt_pr,
            "status": status,
            "language": post_data['language'],
            "stars":post_data['stars'],
            "at_submission": get_phases(project, pull_number, PHASE.at_submission, timelines), #process_submission_phase(project, pull_number),
            "at_review":  get_phases(project, pull_number, PHASE.at_review, timelines),
            "at_waiting_before_change":  get_phases(project, pull_number, PHASE.at_waiting_before_change, timelines),
            "at_changed": get_phases(project, pull_number, PHASE.at_change, timelines),
            "at_waiting_after_accepted":get_phases(project, pull_number, PHASE.at_waiting_after_acceptance, timelines),
            "at_resolution": get_phases(project, pull_number, PHASE.at_resolution, timelines),#at_resolution
            #process_resolution_phase(project, pull_number,'merged') if status == 'merged' else process_resolution_phase(project, pull_number,'closed')
        }
        
        if project not in indexes:
            phases[project] = pulls
            indexes[project] = pulls
            index+=1
            project_list.append(phases)
            phases = {}
        else:
            project_list[index-1][project].update(pulls)
       
    with open("project_phases.json", "w") as final:
        json.dump(project_list, final, indent=1, default=str)
        


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop processing phase")
        exit(1)
