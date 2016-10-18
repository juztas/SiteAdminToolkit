#! /usr/bin/env python

"""
This script is located as ``SiteAdminToolkit/unmerged-cleaner/UnmergedCleaner.py``.
It is used to clean up unmerged files, leaving protected directories alone.
In order to use the script at your site, make sure the
:py:func:`get_unmerged_location` returns the correct location,
based on your node's hostname.
To check this quickly, run the following from ``SiteAdminToolkit/unmerged-cleaner``::

    python -c 'import UnmergedCleaner; print UnmergedCleaner.get_unmerged_location()'

:author: Chistoph Wissing <christoph.wissing@desy.de>
"""

import httplib
import subprocess
import json
import socket
import ssl


def unmerged_from_phedex(site_name):
    """
    Get the unmerged folder location from Phedex.

    :param str site_name: is the name of the site to check
    :returns: lfn of the unmerged folder
    :rtype: str
    """

    conn = httplib.HTTPSConnection('cmsweb.cern.ch',
                                   context=ssl._create_unverified_context())

    try:
        conn.request('GET', 
                     '/phedex/datasvc/json/prod/lfn2pfn?'
                     'node=%s&protocol=direct&lfn=/store/unmerged/' %
                     site_name)
                     
        res = conn.getresponse()
        result = json.loads(res.read())
    except Exception:
        print 'Failed to get LFNs from Phedex...'
        exit(1)

    location = result['phedex']['mapping'][0]['pfn']

    conn.close()

    return location
    

def get_unmerged_location():
    """
    Each site admin should ensure that this function returns the
    correct location of their unmerged directory.
    The easiest way to do this is to add to the dictionary in the function,
    which gives the unmerged location if the key matches part of the hostname.

    :returns: the unmerged directory PFN.
    :rtype: str
    """

    host = socket.gethostname()

    # Try mapping directly the domain to the LFN

    unmerged_pfn_map = {
        'desy.de': unmerged_from_phedex('T2_DE_DESY'),
        'mit.edu': unmerged_from_phedex('T2_US_MIT'),
        }

    for check, item in unmerged_pfn_map.iteritems():
        if check in host:
            return item

    # Fall back to trying to match patterns of all site names

    try:
        import CMSToolBox.sitereadiness

        for site in CMSToolBox.sitereadiness.site_list():
            if site.split('_')[2].lower() in host:
                return unmerged_from_phedex(site)

    except ImportError:
        print 'CMSToolBox not installed...'

    # Cannot find a possible unmerged location

    print 'Cannot determine location of unmerged directory from hostname.'
    print 'Please edit the function get_unmerged_location().'

    exit(1)


def get_protected():
    """
    :returns: the protected directory LFNs.
    :rtype: list
    """

    url = 'cmst2.web.cern.ch'
    conn = httplib.HTTPSConnection(url)

    try:
        conn.request('GET', '/cmst2/unified/listProtectedLFN.txt')
        res = conn.getresponse()
        result = json.loads(res.read())
    except Exception:
        print 'Cannot read Protected LFNs. Have to stop...'
        exit(1)

    protected = result['protected']

    conn.close()

    return protected


def get_unmerged_files():
    """
    :returns: the old files in the unmerged directory
    :rtype: list
    """

    find_cmd = 'find {0} -type f -ctime +14 -print'.format(get_unmerged_location())
    out = subprocess.Popen(find_cmd, shell=True, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, _ = out.communicate()
    return stdout.decode().split()

    # Testing
    # f=open('old_unmerged.txt')
    # return f.readlines()


def lfn2pfn(lfn):
    """
    :param str lfn: is the LFN of a file
    :returns: the PFN, based on :py:func:`get_unmerged_location`
    :rtype: str
    """

    pfn = lfn.replace('/store/unmerged/', '{0}/'.format(get_unmerged_location()))
    return pfn


def do_delete(pfn):
    """Deletes a file based off the PFN

    .. warning::

       Needs to be implimented

    :param str pfn: the PFN of the file to delete
    """

    print 'Would delete %s' % pfn


def filter_protected(unmerged_files, protected):
    """
    Deletes unprotected files.

    :param list unmerged_files: the list of files to check and delete, if unprotected.
    :param list protected: the list of protected LFNs.
    """

    print 'Got %i deletion candidates' % len(unmerged_files)
    print 'Have %i protcted dirs' % len(protected)
    n_protect = 0
    n_delete = 0
    for unmerged_file in unmerged_files:
        # print 'Checking file %s' %file
        protect = False

        for lfn in protected:
            pfn = lfn2pfn(lfn)
            if pfn in unmerged_file:
                print '%s is protected by path %s' % (unmerged_file, pfn)
                protect = True
                break

        if not protect:
            do_delete(unmerged_file)
            n_delete += 1
        else:
            n_protect += 1

    print 'Number deleted: %i,\nNumber protected: %i' % (n_delete, n_protect)


if __name__ == '__main__':
    filter_protected(get_unmerged_files(), get_protected())
