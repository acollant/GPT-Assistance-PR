
import pathlib

import joblib
import pandas as pd

from common import cleanup_files, force_refresh, get_logger, get_path, import_events, initialize

initialize()


def extract_projects(file):
    logger = get_logger(__file__)
    logger.info(f"{file}: Extracting projects")
    projects = (
        import_events(file)
        .query("""payload.str.contains('"pull_request"')""")["repo"]
        .apply(lambda project: project["id"])
        .unique()
    )
    return {"date": file.stem, "count": len(projects), "projects": projects}


def export_projects(projects):
    projects = pd.DataFrame(projects)
    projects.drop(columns="projects").sort_values("date").to_csv(get_path("usage"), index=False)
    projects["projects"].explode().drop_duplicates().sort_values(key=lambda project: project.astype(int)).to_csv(
        get_path("projects_extracted"), header=["id"], index=False
    )


def main():
    if cleanup_files(["usage", "projects_extracted"], force_refresh()):
        with joblib.Parallel(n_jobs=-1, verbose=1) as parallel:
            export_projects(
                parallel(joblib.delayed(extract_projects)(file) for file in pathlib.Path(".").glob("*.json"))
            )
    else:
        print("Skip extracting projects")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop extracting projects")
        exit(1)
