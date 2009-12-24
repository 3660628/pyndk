# -*- coding: utf-8 -*-

"""
summery:  
    auto publish tools
author: 
    cui shaowei
"""

import os
import sys
from xml.dom import minidom
version = ""

proj_name = "pyndk"

def svn_rivision():
    try:
        os.system("svn update -q")
    except: pass
    #dom = minidom.parse(os.path.join(".", ".svn/entries"))
    #return dom.getElementsByTagName('entry')[0].getAttribute('revision')
    n = 0
    for l in open('.svn/entries', 'r'):
        n += 1
        if n == 4:
            return l.strip()
def svn_commit():
    try:
        os.system("svn commit -q")
    except: pass

def update_version():
    global version
    v = svn_rivision()
    v = int(v) + 1
    s = open('%s/__init__.py' % proj_name, 'r').readlines()[0].strip()
    import re
    s = re.sub(r'svn-\d+', 'svn-%d' % v, s)
    print(s)
    open('%s/__init__.py' % proj_name, 'w').write(s)
    version = s.split('"')[1]

def build_changelog():
    change_log = proj_name.upper() + " " + "CHANGES" + os.linesep
    change_log += "=" * 28 + os.linesep * 2
    change_log += "Changes in %s" % version + os.linesep
    change_log += "-" * 28 + os.linesep * 2
    complete = True
    while True:
        header = "* "
        line = raw_input(header)
        line = unicode(line, 'utf-8').strip()

        if len(line) == 0: continue
        if line == u"q": break

        if complete: line = header +line

        if line[-1] == u'\\':
            change_log += line[:-1] + os.linesep
            complete = False
            continue
        change_log += line + os.linesep * 2
        complete = True
    return change_log

def append_changelog(clname, change_log):
    # append changelog
    change_log = change_log.encode('utf-8')
    old_log = change_log
    if os.path.exists(clname):
        old_log = open(clname).read()
    if old_log != change_log:
        sep = '=' * 28 + os.linesep * 2
        pos = old_log.find(sep)
        logs = old_log[:pos + len(sep)] \
                + change_log[pos + len(sep):] \
                + old_log[pos + len(sep):]
    else:
        logs = change_log
    open(clname, "wt").write(logs)

def build_package():
    import tarfile
    mode = "w"
    pname = "%s-%s.%s" % (proj_name, version, "tar.gz")
    tf = tarfile.open(pname, mode)
    try:
        for r, dirs, files in os.walk("."):
            if r.find('.svn') != -1 or r.find('tmp') != -1: continue
            for file in files:
                if file != os.path.split(pname)[1] and \
                        os.path.splitext(file)[-1] not in ('.txt', '.swp', '.pyc', '.pyo'):
                    tf.add(os.path.join(r, file)) 
    finally:
        tf.close()

if __name__ == '__main__':
    update_version()
    append_changelog("ChangeLog", build_changelog())
    build_package()
    svn_commit()
