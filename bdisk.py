#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import re
import urllib
import urllib2
import cookielib
import json
import time

import atexit


def strip_url(u):
    return u.replace('&amp;', '&')

__cookies__ = os.path.join(os.path.dirname(__file__), 'cookies.txt')

cj = cookielib.LWPCookieJar(__cookies__)
cj.load()
atexit.register(lambda : cj.save())

cp = urllib2.HTTPCookieProcessor(cj)
opener = urllib2.build_opener(cp)
opener.addheaders = [
    ('User-agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/535.24 ' \
         '(KHTML, like Gecko) Chrome/19.0.1056.0 Safari/535.24'),]



resp = opener.open("http://pan.baidu.com/")

remain = ''

for line in resp:
    if 'remainingSpace' in line:
        remain = remain or re.sub(r'<.*?>', '', line).strip()

print remain


def timestamp():
    return str(int(time.time() * 1000))


def format_size(num, unit='B'):
    next_unit_map = dict(B="K", K="M", M="G", G="T")
    if num > 1024:
        return format_size(num/1024, next_unit_map[unit])
    if num == 0:
        return "0%s  " % unit   # padding
    if unit == 'B':
        return "%.0f%s" % (num, unit)
    return "%.1f%s" % (num, unit)

TASK_STATUS = {0: u'\u4e0b\u8f7d\u6210\u529f',
               1: u'\u4e0b\u8f7d\u8fdb\u884c\u4e2d',
               2: u'\u7cfb\u7edf\u9519\u8bef',
               3: u'\u8d44\u6e90\u4e0d\u5b58\u5728',
               4: u'\u4e0b\u8f7d\u8d85\u65f6',
               5: u'\u8d44\u6e90\u5b58\u5728\u4f46\u4e0b\u8f7d\u5931\u8d25',
               6: u'\u5b58\u50a8\u7a7a\u95f4\u4e0d\u8db3',
               7: u'\u4efb\u52a1\u53d6\u6d88',
               8: u'\u76ee\u6807\u5730\u5740\u6570\u636e\u5df2\u5b58\u5728',
               9: u'\u4efb\u52a1\u5220\u9664'}

class NetDisk(object):
    def __init__(self, opener):
        self.urlopen = opener.open

    def _bduss(self):
        for c in cj:
            if c.name == 'BDUSS' and c.domain.endswith('.baidu.com'):
                return c.value
        raise RuntimeError('BDUSS cookie not found')

    def _wget_analytics(self, method='http'):
        params = dict(_lsid = timestamp(),
                      _lsix = 1,
                      page = 1,
                      clienttype = 0,
                      type = 'offlinedownloadtaskmethod',
                      method = 'http')
        query = urllib.urlencode(params)
        resp = self.urlopen("http://pan.baidu.com/api/analytics?" + query)
        ret = json.load(resp)
        if ret['errno'] != 0:
            raise RuntimeError('method not supported')

    def wget(self, url):
        self._wget_analytics()
        params = dict(method = 'add_task',
                      app_id = 250528,
                      BDUSS = self._bduss(),
                      source_url = url,
                      save_path = '/')

        req = urllib2.Request("http://pan.baidu.com/rest/2.0/services/cloud_dl?",
                              urllib.urlencode(params))
        resp = self.urlopen(req)
        ret = json.load(resp)
        return ret['task_id']

    def status(self, task_id):
        taskids = ','.join(task_id) if isinstance(task_id, (list, tuple)) else str(task_id)
        params = dict(method = 'query_task',
                      app_id = 250528,
                      BDUSS = self._bduss(),
                      task_ids = taskids,
                      op_type = 1,
                      t = timestamp())
        req = urllib2.Request("http://pan.baidu.com/rest/2.0/services/cloud_dl?" + \
                                  urllib.urlencode(params))
        resp = self.urlopen(req)
        ret = json.load(resp)
        for tid, task in ret['task_info'].items():
            if task.get('finish_time', 0):
                desc = u"完成于 " + time.ctime(int(task['finish_time']))
            else:
                try:
                    desc = u"%3.2f%%" % (int(task['finished_size']) / int(task['file_size']) * 100)
                except:
                    desc = u'未知状态'
            print tid, TASK_STATUS[int(task['status'])], desc
        return ret['task_info']

    def watch(self, task_id):
        while True:
            tasks = self.status(task_id)
            #print tasks
            if any(map(lambda t: int(t['status']) == 1, tasks.values())):
                time.sleep(4)
                continue
            break
        return

    def list(self, dir="/", page=1, initialCall=True):
        params = dict(channel='chunlei',
                      clienttype=0,
                      web=1,
                      num=100,
                      t=timestamp(),
                      page=page,
                      dir=dir,
                      _=timestamp())
        req = urllib2.Request("http://pan.baidu.com/api/list?" + \
                                  urllib.urlencode(params))
        resp = self.urlopen(req)
        ret = json.load(resp)

        files = ret['list']
        if len(files) == 100:
            files.extend(self.list(dir, page=page+1, initialCall=False))
        if initialCall == False: # this is a paging req
            return files
        print "total", len(files), dir
        for f in files:
            if f['isdir'] == 1:
                print 'd',
            else:
                print '-',
            print '\t', format_size(f.get('size', 0)),
            print '\t', time.strftime("%Y-%m-%d %H:%M",
                                      time.localtime(f['server_mtime'])),
            print '\t', f['server_filename']
        return files

    def remove(self, path):
        """remove file(s)"""
        paths = path if isinstance(path, (list, tuple)) else [path]
        params = dict(filelist=json.dumps(paths))
        req = urllib2.Request("http://pan.baidu.com/api/filemanager?"
                              "channel=chunlei&clienttype=0&web=1&opera=delete",
                              urllib.urlencode(params))
        resp = self.urlopen(req)
        ret = json.load(resp)
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret

    def rename(self, path, newname):
        newname = os.path.basename(newname)
        params = dict(filelist=json.dumps([dict(path=path,
                                                newname=newname)]))
        req = urllib2.Request("http://pan.baidu.com/api/filemanager?"
                              "channel=chunlei&clienttype=0&web=1&opera=rename",
                              urllib.urlencode(params))
        resp = self.urlopen(req)
        ret = json.load(resp)
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret

    def move(self, src, dst):
        params = dict(filelist=json.dumps([dict(path=src,
                                                dest=os.path.dirname(dst),
                                                newname=os.path.basename(dst))]))
        req = urllib2.Request("http://pan.baidu.com/api/filemanager?"
                              "channel=chunlei&clienttype=0&web=1&opera=move",
                              urllib.urlencode(params))
        resp = self.urlopen(req)
        ret = json.load(resp)
        if ret['errno'] == 0:
            for i in ret['info']:
                print i['path'], i['errno'] == 0
        else:
            print "error:", ret

    def quota(self):
        resp = self.urlopen("http://pan.baidu.com/api/quota?channel=chunlei&clienttype=0&web=1&t=" + timestamp())
        ret = json.load(resp)
        if ret['errno'] == 0:
            print ret['used'], "/", ret['total']
            print "%3.2f%%" % (ret['used'] / ret['total'] * 100)
        else:
            print 'error', ret


def usage():
    print '= subcommands'
    print 'wget [url]'
    print 'status [taskid]'
    print 'watch [taskid]'
    print 'ls(list) [path]'
    print 'du(quota)'
    print 'mv(move) [src] [dst]'
    print 'rename [old] [new]'
    print 'rm(remove) [path]'

def main():
    if len(sys.argv) < 2:
        print "usage: %s cmd [args]" % sys.argv[0]
        usage()
        sys.exit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    c = NetDisk(opener)

    if cmd == 'wget':
        url = args[0]
        tid = c.wget(url)
        print tid
        c.watch(tid)
    elif cmd == 'status':
        c.status(args)
    elif cmd == 'watch':
        c.watch(args)
    elif cmd in ['ls', 'list']:
        dir = args[0] if args else '/'
        c.list(dir)
    elif cmd in ['quota', 'du']:
        c.quota()
    elif cmd in ['remove', 'rm']:
        c.remove(args)
    elif cmd == 'rename':
        c.rename(*args)
    elif cmd in ['mv', 'move']:
        c.move(*args)
if __name__ == '__main__':
    #c = NetDisk(opener)
    #c.wget("http://www.baidu.com")
    main()
