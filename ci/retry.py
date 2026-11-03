"""Verify a complete source build before retrying its signed publication."""

import json
import os
from pathlib import Path
import re

from publish import publication_rows


def source_identity(run, jobs, matrix, repository):
    if (run['status'] != 'completed' or run['event'] != 'workflow_dispatch'
            or run['head_branch'] != 'main' or run['path'] != '.github/workflows/build.yml'
            or run['head_repository']['full_name'] != repository):
        raise ValueError('Source must be a completed manual main build in this repository')
    rows = publication_rows(matrix)
    if (not re.fullmatch(r'[0-9a-f]{40}', run['head_sha'])
            or run['run_attempt'] < 1):
        raise ValueError('Invalid source identity')
    matrix_jobs = [job for job in jobs if job['name'] == 'generate-matrix']
    builds = [job for job in jobs if job['name'].startswith('build (')]
    if (len(matrix_jobs) != 1 or matrix_jobs[0]['conclusion'] != 'success'
            or len(builds) != len(matrix['include'])):
        raise ValueError('Source run does not contain the complete expected build matrix')
    # 24.10 remains best-effort. Require each exact 25.12 architecture job.
    for row in rows:
        prefix = f"build ({row['version']}, {row['package_arch']}, {row['target']}, "
        matches = [job for job in builds if job['name'].startswith(prefix)]
        if len(matches) != 1 or matches[0]['conclusion'] != 'success':
            raise ValueError(f"Missing or unsuccessful required build: {row['package_arch']}")
    return {'commit': run['head_sha'], 'run_id': str(run['id']),
            'run_attempt': str(run['run_attempt'])}, rows[0]['image']


def main():
    run = json.loads(Path('source-run.json').read_text())
    pages = json.loads(Path('source-jobs.json').read_text())
    jobs = [job for page in pages for job in page['jobs']]
    matrix = json.loads(Path('expected/publication-matrix.json').read_text())
    identity, image = source_identity(run, jobs, matrix, os.environ['GITHUB_REPOSITORY'])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'image={image}\ncommit={identity["commit"]}\n')
        output.write('identity=' + json.dumps(identity, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
