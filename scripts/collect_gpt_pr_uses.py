import numpy
import json
import pandas as pd
import pathlib
import scipy.stats as stats
import numpy as np

from common import (
    initialize,
    import_project_pulls,
    import_project_timelines,
    count_hours,
    get_logger,
    import_project_timelines_gpt,
)

initialize()
logger = get_logger(__file__, modules={"urllib3": "ERROR"})

def process_review_time(project, pull_number):
    columns_ = ["project","pull_number",
              "event_number_pull","event_pull","actor_pull","time_pull","state_pull","is_bot_pull","is_chatgpt_pull",
              "event_number_review","event_review","actor_review", "time_review","state_review","is_bot_review","is_chatgpt_review"]

    query_ = 'pull_number == ' + str(pull_number)
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: process_review_time")

    df_review_ = pd.DataFrame()#(columns=columns_)
    df_review_ = pd.DataFrame()

    #get the pr identified as for assistance
    timelines =  import_project_timelines_gpt(project).query(query_)[["pull_number",
              "event_number","event_x","actor","time","state","is_bot","is_chatgpt","is_gpt_for","html_url"]]
    
    timelines['project'] = project
    #timelines.reset_index(drop=True)
    #contributor 
    actor = timelines.query("event_number == 0")["actor"].to_string(index=False)
    
    #get the pull event
    timeline_pulled = timelines.query("event_x=='pulled'")

    query_ = "actor != '" + actor + "' and (event_x == 'reviewed' or event_x == 'commented' or event_x == 'line-commented'  or event_x == 'commit-commented' or event_x == 'review-commented')"
    timeline_first_review = timelines.query(query_)
     
    #get the first review
    timeline_first_review = timeline_first_review.head(1)
    
    
    timeline_pulled = timeline_pulled.reset_index()
    timeline_pulled = timeline_pulled.drop(['index'], axis=1)

    timeline_first_review = timeline_first_review.reset_index()
    timeline_first_review = timeline_first_review.drop(['index'], axis=1)
    pull_date =  pd.Timestamp(timeline_pulled["time"][0]).tz_localize(None)
   
    if len(timeline_first_review["event_number"]) > 0 :
       df_review_["project"] = timeline_pulled['project']
       df_review_["pull_number"] = timeline_pulled["pull_number"]
    
       df_review_["event_number_pull"] = timeline_pulled["event_number"]
       df_review_["event_pull"] = timeline_pulled["event_x"]
       df_review_["event_url_pull"] = timeline_pulled["html_url"]
       df_review_["contributor"] = timeline_pulled["actor"]
       df_review_["is_gpt_at_pull"] =  'gpt assistance' if timeline_pulled["is_gpt_for"][0] == "gpt assistance"  else 'gpt no assistance'   
    
       df_review_["event_number_review"] = timeline_first_review["event_number"]
       df_review_["event_review"] = timeline_first_review["event_x"]
       df_review_["event_url_review"] = timeline_first_review["html_url"]
       df_review_["maintainer"] = timeline_first_review["actor"]   
       review_date = pd.Timestamp(timeline_first_review["time"][0]).tz_localize(None) 
       df_review_["is_gpt_for_at_review"] =  'gpt assistance' if timeline_first_review["is_gpt_for"][0] == 'gpt assistance'  else 'gpt no assistance' 
       df_review_["review_time"] =  count_hours(pull_date, review_date) 
    
       pull_event_number_ = str(timeline_pulled["event_number"][0])
       timeline_first_review_ = str(timeline_first_review["event_number"][0])
       query_ = "is_gpt_for == 'gpt assistance' and event_number >" + pull_event_number_ + " and event_number < " + timeline_first_review_
       df_review_["is_gpt_within_review"] =  'gpt no assistance'   
       in_phase_list = timelines.query(query_)
       if len(in_phase_list) > 0 :
           df_review_["is_gpt_within_review"] = 'gpt assistance' #len(in_phase_list)
           
       
    return df_review_

def process_change_time(project, pull_number):
    columns_ = ["project","pull_number",
              "event_number_pull","event_pull","actor_pull","time_pull","state_pull","is_bot_pull","is_chatgpt_pull",
              "event_number_review","event_review","actor_review", "time_review","state_review","is_bot_review","is_chatgpt_review"]

    query_ = 'pull_number == ' + str(pull_number)
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: process_change_time")
     
    pull_first_committed = pd.DataFrame()    
    df_change_ = pd.DataFrame() 
    
    timelines =  import_project_timelines_gpt(project).query(query_)[["pull_number",
              "event_number","event_x","actor","time","state","is_bot","is_chatgpt", "is_gpt_for","html_url"]]
    timelines['project'] = project
    
    actor = timelines.query("event_number == 0")["actor"].to_string(index=False)
    query_ = "actor != '" + actor + "' and (event_x == 'reviewed' or event_x == 'commented' or event_x == 'line-commented'  or event_x == 'commit-commented' or event_x == 'review-commented')"
    timeline_last_review = timelines.query(query_).tail(1)
    timeline_last_review = timeline_last_review.reset_index()
    timeline_last_review = timeline_last_review.drop(['index'], axis=1)


    df_change_["project"] = project
    df_change_["pull_number"] =  pull_number
    if len(timeline_last_review) > 0:
        df_change_["project"] = timeline_last_review['project']
        df_change_["pull_number"] =   timeline_last_review["pull_number"]
        df_change_["event_number_last_revision"] = timeline_last_review["event_number"]
        df_change_["event_last_revision"] = timeline_last_review["event_x"]
        df_change_["event_url_last_revision"] = timeline_last_review["html_url"]
        df_change_["maintainer_last_revision"] = timeline_last_review["actor"]
        df_change_["is_chatgpt_last_revision"] =  'gpt assistance' if timeline_last_review["is_gpt_for"][0] == "gpt assistance"  else 'gpt no assistance'
        last_review_date =  pd.Timestamp(timeline_last_review["time"][0]).tz_localize(None)
        
        pull_event_number_ = str(timeline_last_review["event_number"][0])
        query_ = "actor == '" + actor + "' and (event_x == 'committed' or event_x == 'head_ref_force_pushed' or event_x == 'review-commented' or event_x == 'review'  or event_x == 'line-commented' or event_x == 'commit-commented') and  event_number >" + pull_event_number_
        pull_first_committed = timelines.query(query_)#()"event == 'committed' and event_number >" + pull_event_number_ )
        
        pull_first_committed = pull_first_committed.reset_index()
        pull_first_committed = pull_first_committed.drop(['index'], axis=1)
        if len(pull_first_committed) > 0 :
            timeline_first_committed_ = str(pull_first_committed["event_number"][0])
            query_ = "is_gpt_for == 'gpt assistance' and event_number >=" + pull_event_number_ + " and event_number <= " + timeline_first_committed_
            in_phase_list = timelines.query(query_)
            first_commit_date = pd.Timestamp(pull_first_committed["time"][0]).tz_localize(None) 
            df_change_["event_number_acceptance"] = pull_first_committed["event_number"]
            df_change_["event_acceptance"] = pull_first_committed["event_x"]
            df_change_["event_url_acceptance"] = pull_first_committed["html_url"]
            df_change_["contributor_acceptance"] = pull_first_committed["actor"]
            df_change_["time_acceptance"] = count_hours(  last_review_date, first_commit_date) 
            df_change_["is_chatgpt_for_acceptance"] = 'gpt assistance' if pull_first_committed["is_gpt_for"][0] != '' else 'gpt no assistance'
            
            df_change_["is_gpt_within_acceptance"] = 'gpt no assistance'
            if len(in_phase_list) > 0 :
                df_change_["is_gpt_within_acceptance"] = 'gpt assistance' #len(in_phase_list)
           
    return df_change_

def is_merged(project, pull_number):
    query_ = 'pull_number == ' + str(pull_number)
    timelines = import_project_timelines(project).query(query_)
    
    return (len(timelines.query("event == 'merged'")) > 0)
     

def use_cases():
    projects = []
    gpt_pulls = import_project_pulls().sort_values(by='owner_login')
    df_RQ3 = pd.DataFrame()
    for _, row in gpt_pulls.iterrows():#get_project():
        project = row['owner_login'] + '_' + row['name']
        pull_number = row['number']
        is_gpt = row['is_gpt']
        if is_merged(project, pull_number) == True:
            df_r = process_review_time(project, pull_number)
            df_c = process_change_time(project, pull_number)
            if len(df_r) > 0:
                df_RQ3 = df_RQ3._append(df_r.merge(df_c, how='left', on=["project", "pull_number"]))
            else :
                df_RQ3 = df_RQ3._append(df_c)
    
    df_RQ3.to_csv('RQ3_data.csv', index=False)
   
    
    df_sample =  df_RQ3.sample(300)
    df_sample.to_csv('RQ3_sample.csv', index=False)



def main():
    use_cases()
   


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop collecting data")
        exit(1)