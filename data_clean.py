import os


def find_batch_files(category, scenarios_dir):
    """
    Scan the scenario directory and return a list of full file paths
    for all batch CSVs belonging to the given category.

    Excludes the master CSV that does not contain a 'batch' name
    """
    batch_files = []

    for filename in os.listdir(scenarios_dir):
        if (
            filename.startswith(category)
            and filename.endswith(".csv")
            and "batch" in filename
        ):
            full_path = os.path.join(scenarios_dir, filename)
            batch_files.append(full_path)

    return batch_files


def load_and_merge(csv):
    pass


def dedup_and_write(csv):

    pass
