"""
Downloads source releases from Sourceforge and puts them into a git repository
"""

import json
import datetime
from utils.utils import *


if __name__ == '__main__':

    # https://sourceforge.net/projects/phaosrpg/files/OldFiles/Pv0.7devel.zip/download is a corrupt zip

    # base path is the directory containing this file
    base_path = os.path.abspath(os.path.dirname(__file__))
    print('base path={}'.format(base_path))

    # recreate archive path
    archive_path = os.path.join(base_path, 'downloads')
    if not os.path.exists(archive_path):
        os.mkdir(archive_path)

    # load source releases urls
    with open(os.path.join(base_path, 'phaos.json'), 'r') as f:
        urls = json.load(f)
    print('will process {} urls'.format(len(urls)))
    if len(urls) != len(set(urls)):
        raise RuntimeError("urls list contains duplicates")

    # determine file archives from urls
    archives = [x.split('/')[-2] for x in urls]
    if len(archives) != len(set(archives)):
        raise RuntimeError("files with duplicate archives, cannot deal with that")

    # determine version from file name
    versions = [determine_archive_version_generic(x, leading_terms=['phaos-', 'phaos', 'pv'], trailing_terms=['zip']) for x in archives]
    # for version in versions:
    #     print(version)

    # extend archives to full paths
    archives = [os.path.join(archive_path, x) for x in archives]

    # download them
    print('download source releases')
    for url, destination in zip(urls, archives):
        # only if not yet existing
        if os.path.exists(destination):
            continue
        # download
        print('  download {}'.format(os.path.basename(destination)))
        with urllib.request.urlopen(url) as response:
            with open(destination, 'wb') as f:
                shutil.copyfileobj(response, f)
                time.sleep(1) # we are nice

    # unzip them
    print('unzip downloaded archives')
    unzipped_archives = [x[:-4] for x in archives] # folder is archive name without .zip
    for archive, unzipped_archive in zip(archives, unzipped_archives):
        print('  unzip {}'.format(os.path.basename(archive)))
        # only if not yet existing
        if os.path.exists(unzipped_archive):
            continue
        os.mkdir(unzipped_archive)
        # unzip
        unzip_keep_last_modified(archive, unzipped_archive)

    # go up in unzipped archives until the very first non-empty folder
    unzipped_archives = [strip_wrapped_folders(x) for x in unzipped_archives]

    # determine date
    dates = [determine_latest_last_modified_date(x) for x in unzipped_archives]
    dates_strings = [datetime.datetime.fromtimestamp(x).strftime('%Y-%m-%d') for x in dates]
    # if len(dates_strings) != len(set(dates_strings)):
    #     raise RuntimeError("Some on the same day, cannot cope with that")

    # gather all important stuff in one list and sort by dates
    db = list(zip(urls, unzipped_archives, versions, dates, dates_strings))
    db.sort(key=lambda x:x[3])
    print('proposed order')
    for url, _, version, _, date in db:
        print('  date={} version={}'.format(date, version))

    # git init
    git_path = os.path.join(base_path, 'phaosrpg')
    if os.path.exists(git_path):
        shutil.rmtree(git_path)
    os.mkdir(git_path)
    os.chdir(git_path)
    subprocess_run(['git', 'init'])
    subprocess_run(['git', 'config', 'user.name', 'Trilarion'])
    subprocess_run(['git', 'config', 'user.email', 'Trilarion@users.noreply.gitlab.com'])

    # now process revision by revision
    print('process revisions')
    git_author = 'eproductions3 <eproductions3@user.sourceforge.net>'
    for url, archive_path, version, _, date in db:
        print('  process version={}'.format(version))

        # clear git path without deleting .git
        print('    clear git')
        for item in os.listdir(git_path):
            # ignore '.git
            if item == '.git':
                continue
            item = os.path.join(git_path, item)
            if os.path.isdir(item):
                shutil.rmtree(item)
            else:
                os.remove(item)

        # copy unpacked source files to git path
        print('copy to git')
        copy_tree(archive_path, git_path)

        # update the git index (add unstaged, remove deleted, ...)
        print('git add')
        os.chdir(git_path)
        subprocess_run(['git', 'add', '--all'])

        # perform the commit
        print('git commit')
        os.chdir(git_path)
        message = 'version {} ({}) on {}'.format(version, url, date)
        print('  message "{}"'.format(message))
        subprocess_run(['git', 'commit', '--message={}'.format(message), '--author={}'.format(git_author), '--date={}'.format(date)])