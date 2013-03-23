#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cmd import Cmd
import bdisk
import os

class YunCmd(Cmd):
    prompt = "☁ > "
    intro = "Baidu Yun cli <andelf@gmail.com>"
    def __init__(self, client):
        Cmd.__init__(self)

        self._c = client
        self._cp = '/'

    def do_ls(self, path):
        path = self._cp if path == '' else path
        self._c.list(path)

    def do_cd(self, path):
        if path == '':
            self._cp = '/'
        else:
            p = os.path.normpath(os.path.join(self._cp, path))
            self._cp = p

    def do_du(self, *args):
        self._c.quota()

    def do_pwd(self, *args):
        print self._cp

if __name__ == '__main__':
    client = bdisk.NetDisk(bdisk.opener)
    c = YunCmd(client)
    c.cmdloop()
