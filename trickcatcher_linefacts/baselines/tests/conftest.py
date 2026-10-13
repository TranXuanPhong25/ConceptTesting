"""Generated pytest scripts are artifacts, not this adapter's unit tests."""


def pytest_ignore_collect(collection_path, config):
    return collection_path.is_dir() and (
        collection_path.name in {'dry_runs', '.pytest_tmp'}
        or (collection_path/'manifest.json').is_file()
    )
