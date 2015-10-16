'''
Gets version information from git 
and puts it in _generated_version.py
like so:

FULL_VERSION="2.2.2-304-gc3231cb"
STRICT_VERSION="2.2.2"

'''
import os
import subprocess

TAG_PREFIX = "release-"
GENERATED_VERSION_PY = """
# This file is originally generated from Git information by running 'setup.py
# version'. Distribution tarballs contain a pre-generated copy of this file.

__version__ = '%s'
FULL_VERSION = '%s'
"""
VERSION_FILE="_generated_version.py"
def update_version_py():
    if not os.path.isdir("../.git"):
        print "This does not appear to be a Git repository."
        return
    try:
        p = subprocess.Popen(["git", "describe",
                              "--tags", "--always"],
                             stdout=subprocess.PIPE)
    except EnvironmentError:
        print "unable to run git, leaving %s alone" % VERSION_FILE
        return
    stdout = p.communicate()[0]
    if p.returncode != 0:
        print "unable to run git, leaving %s alone" % VERSION_FILE
        return
    # we use tags like "python-ecdsa-0.5", so strip the prefix
    assert stdout.startswith(TAG_PREFIX)
    full_version = stdout[len(TAG_PREFIX):].strip()
    if '-' in full_version:
        strict_version = full_version[:full_version.find('-')] 
    f = open(VERSION_FILE, "w")
    f.write(GENERATED_VERSION_PY % (strict_version, full_version))
    f.close()
    print "updated _generated_version.py to '%s'" % strict_version


if __name__ == '__main__':
    update_version_py()