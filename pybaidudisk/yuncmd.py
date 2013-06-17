#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import shlex
import sys
from cmd import Cmd

import disk
from utils import format_size


class YunCmd(Cmd):
    prompt = "☁ > "
    intro = "Baidu Yun cli"
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
        return map(lambda f: ('"%s"') % f if ' ' in f else f, ret)

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
    complete_rename = _complete_a_path

    def do_ls(self, arg):
        """ls: list dir content
        ls [dir_name]
        """
        try:
            path, = shlex.split(arg)
            path = os.path.normpath(os.path.join(self._cp, path))
        except:
            path = self._cp
        files = self._c.list(path)
        if files:
            print "total", len(files), path
            for f in files:
                if f['isdir'] == 1:
                    print 'd',
                else:
                    print '-',
                print '\t', format_size(f.get('size', 0)),
                print '\t', time.strftime("%Y-%m-%d %H:%M",
                                          time.localtime(f['server_mtime'])),
                print '\t', f['server_filename']
        else:        
            print "no such dir"

    def do_rm(self, arg):
        """rm: remove file or dir
        rm dir_name
        rm file_name
        """
        path, = shlex.split(arg)
        path = os.path.normpath(os.path.join(self._cp, path))
        ret = self._c.remove(path)
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret
            
    def get_status(self, task_id):        
        ret = self._c.status(task_id)
        for tid, task in ret['task_info'].items():
            if task.get('finish_time', 0):
                desc = u"完成于 " + time.ctime(int(task['finish_time']))
            else:
                try:
                    desc = u"%3.2f%%" % (float(task['finished_size']) / int(task['file_size']) * 100)
                except:
                    desc = u'未知状态'
            print tid, disk.TASK_STATUS[int(task.get('status', 0))], desc
        return ret    
            
    def do_status(self, task_id):        
        '''
        status task_id
        '''
        self.get_status(task_id)
            
    def do_rename(self, arg):        
        '''
        rename path newpath
        '''
        path, newpath = shlex.split(arg)
        path = os.path.normpath(os.path.join(self._cp, path))
        newpath = os.path.normpath(os.path.join(self._cp, newpath))
        ret = self._c.rename(path, newpath)        
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret

    def do_mv(self, arg):
        """mv: move file or dir
        mv src dst
        """
        src, dst = shlex.split(arg)
        fname = os.path.basename(src)
        src = os.path.normpath(os.path.join(self._cp, src))
        dst = os.path.normpath(os.path.join(self._cp, dst))
        if self._c.isdir(dst):
            ret = self._c.move(src, dst, fname)
        else:
            ret = self._c.move(src, os.path.dirname(dst), os.path.basename(dst))
            
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret
            
    def do_quota(self, _):        
        '''disk usage'''
        ret = self._c.quota()
        if ret['errno'] == 0:
            print format_size(ret['used']), "/", format_size(ret['total'])
            print "%3.2f%%" % (float(ret['used']) / ret['total'] * 100)
        else:
            print 'error', ret
            
    def do_cd(self, path):
        """cd: change directory to
        cd [dir]
        """
        if path == '':
            self._cp = '/'
        else:
            p = os.path.normpath(os.path.join(self._cp, path))
            self._cp = p
            
    def do_upload(self, arg):        
        """upload: upload file to dst
        upload file dst
        """
        args = shlex.split(arg)
        
        if len(args) == 2:
            local, remote = args
        else:    
            local, = args
            remote = self._cp
            
        if os.path.isfile(local):        
            ret = self._c.upload(local, remote)
            if ret['errno'] == 0:
                print ret['path'], "save ok!"
            else:
                print 'error', ret
        
    def do_mkdir(self, arg):
        """mkdir: make a new dir
        mkdir [dir_name]
        """
        path, = shlex.split(arg)
        p = os.path.normpath(os.path.join(self._cp, path))
        ret = self._c.mkdir(p)
        if ret['errno'] == 0:
            print ret['path'], "save ok!"
        else:
            print 'error', ret
        
    def do_wget(self, url):
        """wget: download from url
        wget [url]
        """
        print url
        tid = self._c.wget(url, self._cp)
        print "TASK ID =>", tid
        self.do_watch(tid)

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
            print t['task_id'], '\t', disk.TASK_STATUS[int(t['status'])], \
                '\t', t['task_name'], '\t\t', t['source_url']

    def do_watch(self, task_id):
        """watch: watch some task
        watch [task_id]
        """
        while True:
            ret = self.get_status(task_id)
            tasks = ret['task_info']
            if any(map(lambda t: int(t['status']) == 1, tasks.values())):
                time.sleep(6)
                continue
            break
        return
        
    def help_EOF(self):
        print "Quits the program"
        
    def do_EOF(self, line):
        '''Quit'''
        sys.exit()        
        
    def do_exit(self, line):    
        '''Quit'''
        sys.exit()
        
def run_cmd(username, password):        
    client = disk.NetDisk(username, password)
    if client.check_login():
        c = YunCmd(client)
        c.cmdloop()

        
if __name__ == "__main__":        
    import sys
    if len(sys.argv) < 3:
        print "Usage: yuncmd username password"
    else:    
        run_cmd(sys.argv[1], sys.argv[2])