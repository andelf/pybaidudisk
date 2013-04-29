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
import mimetypes
import random

import atexit


def strip_url(u):
    return u.replace('&amp;', '&')

__cookies__ = os.path.join(os.path.dirname(__file__), 'cookies.txt')

cj = cookielib.LWPCookieJar(__cookies__)
cj.load()
#atexit.register(lambda : cj.save())

cp = urllib2.HTTPCookieProcessor(cj)
opener = urllib2.build_opener(cp)
opener.addheaders = [
    ('User-agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/535.24 ' \
         '(KHTML, like Gecko) Chrome/19.0.1056.0 Safari/535.24'),
    ('Referer', 'http://pan.baidu.com/disk/home'),
]

resp = opener.open("http://pan.baidu.com/")

remain = ''

for line in resp:
    if 'remainingSpace' in line:
        remain = remain or re.sub(r'<.*?>', '', line).strip()

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


def mulitpart_urlencode(fieldname, filename, max_size=1024, **params):
    """Pack image from file into multipart-formdata post body"""
    try:
        os.path.getsize(filename)
    except os.error:
        raise IOError('Unable to access file')

    # image must be gif, jpeg, or png
    file_type = mimetypes.guess_type(filename)
    if file_type is None:
        raise QWeiboError('Could not determine file type')
    file_type = file_type[0]

    # build the mulitpart-formdata body
    BOUNDARY = 'ANDELF%s----' % ''.join(
        random.sample('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', 10))
    body = []
    for key, val in params.items():
        if val is not None:
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="%s"' % key)
            body.append('Content-Type: text/plain; charset=UTF-8')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            val = val
            body.append(val)
    fp = open(filename, 'rb')
    body.append('--' + BOUNDARY)
    body.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (fieldname, filename.encode('utf-8')))
    body.append('Content-Type: %s' % file_type)
    body.append('Content-Transfer-Encoding: binary')
    body.append('')
    body.append(fp.read())
    body.append('--%s--' % BOUNDARY)
    body.append('')
    fp.close()
    body.append('--%s--' % BOUNDARY)
    body.append('')
    # fix py3k
    #for i in range(len(body)):
    #    body[i] = body[i]
    body = str('\r\n'.join(body)) #
    # build headers
    headers = {
        'Content-Type': 'multipart/form-data; boundary=%s' % BOUNDARY,
        'Content-Length': len(body)
    }

    return headers, body


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

    def wget(self, url, save_to='/'):
        self._wget_analytics()
        params = dict(method = 'add_task',
                      app_id = 250528,
                      BDUSS = self._bduss(),
                      source_url = url,
                      save_path = save_to)

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
                time.sleep(6)
                continue
            break
        return

    def list_task(self):
        query = dict(method='list_task',
                     app_id=250528,
                     BDUSS=self._bduss(),
                     need_task_info=1,
                     status=255,
                     t=timestamp())
        req = urllib2.Request("http://pan.baidu.com/rest/2.0/services/cloud_dl?" + \
                              urllib.urlencode(query))
        resp = self.urlopen(req)
        ret = json.load(resp)

        tasks = ret['task_info']
        return tasks

    def fetch(self, path):
        pass

    def list(self, dir="/"):
        files = self._list(dir)
        if files is None:
            print 'no such dir'
            return []
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


    def _list(self, dir="/", page=1, initialCall=True):
        # None for error
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
            files.extend(self._list(dir, page=page+1, initialCall=False))
        return files

    def isdir(self, dir):
        parent_path = os.path.dirname(dir)
        dir_name = unicode(os.path.basename(dir), 'utf-8')
        for d in self._list(parent_path):
            if dir_name == d['server_filename']:
                return True
        return False

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
            return True
        else:
            print "error:", ret
            return False

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

    def move(self, src, dst, newname):
        params = dict(filelist=json.dumps([dict(path=src,
                                                dest=dst,
                                                newname=newname or os.path.basename(src))]))
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
            print format_size(ret['used']), "/", format_size(ret['total'])
            print "%3.2f%%" % (ret['used'] / ret['total'] * 100)
        else:
            print 'error', ret

    def upload(self, filepath):
        headers, body = mulitpart_urlencode("Filedata", filepath,
                                            Filename=os.path.basename(filepath),
                                            Upload="Submit Query")
        params = dict(method='upload',
                      type='tmpfile',
                      app_id=250528,
                      BDUSS=self._bduss())
        req = urllib2.Request("http://c.pcs.baidu.com/rest/2.0/pcs/file?" + \
                                  urllib.urlencode(params),
                              body, headers)
        resp = self.urlopen(req)
        ret = json.load(resp)
        size = os.path.getsize(filepath)
        # {"md5":"16c1c8e61670eac54979f3da18b954ab","request_id":839611680}
        return self._create(os.path.join("/", os.path.basename(filepath)),
                            [ret['md5']], size)

    def mkdir(self, path):
        return self._create(path, [], "", isdir=1)

    def _create(self, path, blocks, size, isdir=0):
        params = dict(path = path,
                      isdir = isdir,
                      size = size,
                      block_list = json.dumps(blocks),
                      method = 'post')
        req = urllib2.Request("http://pan.baidu.com/api/create?a=commit&channel=chunlei&clienttype=0&web=1",
                              urllib.urlencode(params))
        resp = self.urlopen(req)
        ret = json.load(resp)
        # {"fs_id":2157439985,"server_filename":"ck.txt","path":"\/ck.txt","size":1728,"ctime":1363701601,"mtime":1363701601,"isdir":0,"errno":0}
        if ret['errno'] == 0:
            print ret['path'], "save ok!"
        else:
            print 'error', ret
        return ret

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
    elif cmd in ['put', 'upload']:
        c.upload(args[0])
    elif cmd in ['md', 'mkdir']:
        c.mkdir(args[0])


if __name__ == '__main__':
    #c = NetDisk(opener)
    #c.wget("http://www.baidu.com")
    main()
