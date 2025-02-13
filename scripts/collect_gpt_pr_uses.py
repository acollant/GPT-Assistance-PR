import numpy
import json
import pandas as pd
import pathlib
import scipy.stats as stats
import numpy as np
import numpy

from common import (
    initialize,
    import_project_timelines,
    count_hours,
    get_logger,
    import_project_timelines_gpt,
)

initialize()
logger = get_logger(__file__, modules={"urllib3": "ERROR"})


     

def get_json(file_name):
    # Opening JSON file
    f = open(file_name,'r')
    # returns JSON object as  a dictionary
    data = json.load(f)
    f.close()
    return  data


def get_sample():

    dict_to_examine = []
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("distance.csv")
    df_ = pd.read_csv(file_path)
    phase = ['at_review', 
            'at_waiting_before_change', 
            'at_changed',
            ]
    
    df_ = df_.reset_index()
    df_ = df_.drop(['index'], axis=1)
    df_x = pd.DataFrame()
    for p in phase:
        print('phase:', p)
        df_sample = df_[(df_['phase']==p)]
        
        df_x = df_x._append(df_sample.sample(1))
        
    df_x = df_x.reset_index()
    df_x = df_x.drop(['index'], axis=1)
    file_path = directory / pathlib.Path("project_phases.json")
    data = get_json(file_path)
    
    for _, row in df_x.iterrows():#get_project():
        project = row['project_gpt'] 
        pull_number = str(row['pull_number_gpt'])
        phase = row['phase']
        labelling = {"phase":phase, "label":"", 'comments':""}
    
        print(f"project:{project} and pull_number:{pull_number} and phase:{phase}")
        dict_project= {}
        dict_pull = {}
        dict_phase = {}
        for all_pr in data:
            dict_project[project] = {}
            if project in all_pr:
                
                dict_phase = all_pr[project][(pull_number)]
                dict_pull[pull_number] = dict_phase
                dict_pull[pull_number]["labelling"] = labelling
                dict_pull[pull_number]["is_GPT_PR"] = all_pr[project][str(pull_number)]["is_GPT_PR"]
                dict_pull[pull_number]["status"] = all_pr[project][str(pull_number)]["status"]
                dict_pull[pull_number]["language"] = all_pr[project][str(pull_number)]["language"]
                dict_pull[pull_number]["stars"] = all_pr[project][str(pull_number)]["stars"]
                
                dict_project[project] = dict_pull
                
                dict_to_examine.append(dict_project)
                print(dict_phase)
                #input('stop')
                break
                
         
    with open("RQ3_to_examine.json", "w") as jsonFile:
        json.dump(dict_to_examine, jsonFile, indent=4)  

def main():
    get_sample()
   
   


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop collecting data")
        exit(1)