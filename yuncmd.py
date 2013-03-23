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
        if len(line) >= 3:
            prefix = line[3:]
        else:
            return []
        return self._complete_path(prefix)

    complete_cd = _complete_a_path
    complete_ls = _complete_a_path
    complete_rm = _complete_a_path
    complete_mv = _complete_a_path

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
        self._c.mkdir(path)

    def do_wget(self, url):
        """wget: download from url
        wget [url]
        """
        tid = self._c.wget(url, self._cp)
        print "TASK ID =>", tid
        self._c.watch(tid)

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

if __name__ == '__main__':
    client = bdisk.NetDisk(bdisk.opener)
    c = YunCmd(client)
    c.cmdloop()
