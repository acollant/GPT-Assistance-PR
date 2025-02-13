import numpy
import json
import pandas as pd
import pathlib
import scipy.stats as stats
import numpy as np
from numpy.linalg import norm

from common import (
    initialize,
    import_project_pulls,
)

initialize()


def get_json(file_name):
    # Opening JSON file
    f = open(file_name,'r')
    # returns JSON object as  a dictionary
    data = json.load(f)
    f.close()
    return  data

def phases_summary_stats():
    
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("project_phases.json")
    data = get_json(file_path)
    
    
    projects = import_project_pulls().sort_values(['owner_login','name'])
    columns_1 = ['phase','is_GPT_PR','pr_status','is_event_gpt','duration']
    columns_2 =['is_GPT_PR','pr_status']
    df_status = pd.DataFrame(columns=columns_2)
    df_stats  = pd.DataFrame(columns=columns_1)

    
   #'at_submission', 
    phases = [
             'at_submission',
             'at_review', 
             'at_waiting_before_change', 
             'at_changed',
             'at_waiting_after_accepted', 
             'at_resolution']

    
    for _, row in projects.iterrows():#get_project():
        project = row['owner_login'] + '_' + row['name']
        pull_number = str(row['number'])
        status_arr = []
        phase_arr = []
        for projects in data:    
            if project in projects:
                is_gpt_pr = 'gpt assistance' if  projects[project][pull_number]['is_GPT_PR'] == 1 else 'not gpt assistance'
                pr_status = projects[project][pull_number]['status']
                status_arr.append([is_gpt_pr, pr_status]) 
                df_2 = pd.DataFrame(status_arr, columns=columns_2) 
                df_status = df_status._append(df_2,ignore_index=True)
                for phase in phases:

                    if  projects[project][pull_number][phase] == None: continue
                    
                    event_gpt = 'gpt assistance'  if projects[project][pull_number][phase]['gpt_assistance']==1 else 'not gpt assistance'
                    duration  = projects[project][pull_number][phase]['duration'] 
                    phase_arr.append([phase, is_gpt_pr, pr_status, event_gpt, duration]) 
                df_1 = pd.DataFrame(phase_arr, columns=columns_1) 
                print(df_1)
        if len(df_1) == 0: continue
        df_stats = df_stats._append(df_1,ignore_index=True)
            
                
    df_stats= df_stats.sort_values('phase')
    
    df_status = df_status.reset_index()
    df_status = df_status.drop(['index'], axis=1)
    
    df_stats = df_stats.reset_index()
    df_stats = df_stats.drop(['index'], axis=1)

    df_summary_status = df_status.groupby(['is_GPT_PR','pr_status']).agg(
        no_status =('pr_status', 'count'),
    ).reset_index()
    print(df_summary_status)
    df_summary_status.to_csv("summary_status.csv", index=False)

    
    
    summary_phases= df_stats.groupby(['phase','is_GPT_PR','is_event_gpt']).agg(
        count = ('is_event_gpt', 'count'),
        median_duration = ('duration', 'median'),
        mean_duration = ('duration', 'mean'),
        max_duration_in_hrs  = ('duration', 'max'),
        min_duration_in_hrs  = ('duration', 'min'),
    ).reset_index()
    print(summary_phases)
    summary_phases.to_csv("summary_phases.csv", index=False)

def stats_distance():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    path = directory / pathlib.Path('distance_all.csv') 
    df_ = pd.read_csv(path)  
    phase = [
        'at_review', 
        'at_waiting_before_change', 
        'at_changed',
        'at_resolution']
    df_ = df_.reset_index()
    df_ = df_.drop(['index'], axis=1)
    summary= df_.groupby(['phase', 'project_gpt','pull_number_gpt']).agg(
        count = ('event_gpt', 'count'),
        manhattan_median = ('manhattan_distance', 'median'),
        manhattan_mean   = ('manhattan_distance', 'mean'),
        manhattan_max  = ('manhattan_distance', 'max'),
        manhattan_min  = ('manhattan_distance', 'min'),
        cosine_simil_median = ('cosine_similarity', 'median'),
        cosine_simil_meam   = ('cosine_similarity', 'mean'),
        cosine_simil_max  = ('cosine_similarity', 'max'),
        cosine_simil_min  = ('cosine_similarity', 'min'),
        euclidean_mediam = ('euclidean_distance', 'median'),
        euclidea_mean   = ('euclidean_distance', 'mean'),
        euclidea_max  = ('euclidean_distance', 'max'),
        euclidea_min  = ('euclidean_distance', 'min'),
        jaccard_simil_median = ('jaccard_similiarity', 'median'),
        jaccard_simil_meam   = ('jaccard_similiarity', 'mean'),
        jaccard_simil_max  = ('jaccard_similiarity', 'max'),
        jaccard_simil_min  = ('jaccard_similiarity', 'min'),
    ).reset_index()
    summary.to_csv('summary_distance.csv')
    print(summary)

def spearmanr():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    path = directory / pathlib.Path('distance_all.csv') 
    df_ = pd.read_csv(path)  
    phase = [
        'at_review', 
        'at_waiting_before_change', 
        'at_changed',
        'at_resolution']
    df_ = df_.reset_index()
    df_ = df_.drop(['index'], axis=1)
    for p in phase:
        print('phase:', p)
        df_x = df_[(df_['phase']==p)]
        df_x = df_x.reset_index()
        df_x = df_x.drop(['index'], axis=1)
        
        x = df_x['manhattan_distance'].tolist() 
        y = df_x['cosine_distance'].tolist()

        corr, pval = stats.spearmanr(x, y)
        # print the result
        print("Spearman's correlation coefficient:", corr)
        print("p-value:", pval)

def main():
    stats_distance()
    spearmanr()
    phases_summary_stats()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop collecting data")
        exit(1)