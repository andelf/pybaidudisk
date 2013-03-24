#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cmd import Cmd
import bdisk
import shlex
import os

class YunCmd(Cmd):
    prompt = "☁ > "
    intro = "Baidu Yun cli <andelf@gmail.com>"
    def __init__(self, client):
        Cmd.__init__(self)

        self._c = client
        self._cp = '/'

    def emptyline(self):
        return

    def _complete_path(self, prefix):
        prefix_name = os.path.basename(prefix)
        if prefix_name:
            parent_path = os.path.dirname(os.path.normpath(os.path.join(self._cp, prefix)))
        else:                   # empty prefix_name
            parent_path = os.path.normpath(os.path.join(self._cp, prefix))
        #print prefix_name, parent_path
        ret = [p['server_filename'] for p in self._c._list(parent_path) if p['server_filename'].startswith(prefix_name)]
        return map(lambda f: ('"%s"') % f if ' ' in f else f,
                   ret)

    def _complete_a_path(self, text, line, begidx, endidx):
        prefix = ''
        try:
            _, prefix = line.split(' ', 1)
        except:
            return []
        return self._complete_path(prefix)

    complete_cd = _complete_a_path
    complete_ls = _complete_a_path
    complete_rm = _complete_a_path
    complete_mv = _complete_a_path
    complete_get = _complete_a_path

    def do_ls(self, arg):
        """ls: list dir content
        ls [dir_name]
        """
        try:
            path, = shlex.split(arg)
            path = os.path.normpath(os.path.join(self._cp, path))
        except:
            path = self._cp
        self._c.list(path)

    def do_rm(self, arg):
        """rm: remove file or dir
        rm dir_name
        rm file_name
        """
        path, = shlex.split(arg)
        path = os.path.normpath(os.path.join(self._cp, path))
        self._c.remove(path)

    def do_mv(self, arg):
        """mv: move file or dir
        mv src dst
        """
        src, dst = shlex.split(arg)
        fname = os.path.basename(src)
        src = os.path.normpath(os.path.join(self._cp, src))
        dst = os.path.normpath(os.path.join(self._cp, dst))
        if self._c.isdir(dst):
            self._c.move(src, dst, fname)
        else:
            self._c.move(src, os.path.dirname(dst), os.path.basename(dst))

    def do_cd(self, path):
        """cd: change directory to
        cd [dir]
        """
        if path == '':
            self._cp = '/'
        else:
            p = os.path.normpath(os.path.join(self._cp, path))
            self._cp = p

    def do_mkdir(self, arg):
        """mkdir: make a new dir
        mkdir [dir_name]
        """
        path, = shlex.split(arg)
        p = os.path.normpath(os.path.join(self._cp, path))
        self._c.mkdir(p)

    def do_wget(self, url):
        """wget: download from url
        wget [url]
        """
        tid = self._c.wget(url, self._cp)
        print "TASK ID =>", tid
        self._c.watch(tid)

    def do_get(self, path):
        """get: open browser and download sth
        get [file_name]
        """
        p = os.path.normpath(os.path.join(self._cp, path))
        filename = os.path.basename(p)
        for f in self._c._list(os.path.dirname(p)):
            if f['server_filename'] == filename:
                url = f['dlink']
                print url

    def do_du(self, _):
        """du: disk usage
        du
        """
        self._c.quota()

    def do_pwd(self, _):
        """pwd: present working directory
        pwd
        """
        print self._cp

    def do_jobs(self, _):
        """jobs: list current download jobs
        jobs
        """
        tasks = self._c.list_task()
        for t in [t for t in tasks if int(t['status']) in [1,0]]:
            print t['task_id'], '\t', bdisk.TASK_STATUS[int(t['status'])], \
                '\t', t['task_name'], '\t\t', t['source_url']

    def do_watch(self, arg):
        """watch: watch some task
        watch [task_id]
        """
        self._c.watch(arg)

if __name__ == '__main__':
    client = bdisk.NetDisk(bdisk.opener)
    c = YunCmd(client)
    c.cmdloop()
