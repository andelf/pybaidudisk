#! /usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import os
import re
import cookielib
import json
import pycurl
import urllib


from utils import parser_json
from netlib import Curl
import utils

loglevel = logging.INFO
console_format = "%(levelname)-8s: %(message)s"
datefmt = "%H:%M:%S"
logging.basicConfig(level=loglevel, format=console_format, datefmt=datefmt)
logger = logging.getLogger(__name__)


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
    
    def __init__(self, username, password):
        self.cookie_file = utils.get_cookie_file(username)
        self.curl = Curl(self.cookie_file)
        self.username = username
        self.password = password
        self.__bduss = None
        
    def get_token(self):    
        url = "https://passport.baidu.com/v2/api/?getapi&tpl=netdisk&apiver=v3&tt=%s&class=login" % utils.timestamp()
        ret = self.api_request(url)
        return ret["data"]["token"]
    
    def get_verifycode(self, code_string):
        url = "https://passport.baidu.com/cgi-bin/genimage?" + code_string
        print url 
        code = raw_input("Please input verifycode > ")
        return code
    
    def check_login(self, stage=0):
        # self.curl.request("http:/pan.baidu.com/")
        
        ret = self.api_request("https://pan.baidu.com/api/account/thirdinfo")
        if ret["errno"] == 0:
            logger.debug("Login check success!")
            return True
        
        # More than twice landing check
        if stage >= 2:
            logger.debug("Login check failed!")
            return False
        
        # Get token
        token = self.get_token()
        
        # Check require verifycode
        params = dict(token=token,
                      tpl="netdisk",
                      apiver="v3",
                      tt=utils.timestamp(),
                      username=self.username,
                      isphone="false")
        check_login_url = "https://passport.baidu.com/v2/api/?logincheck&" + urllib.urlencode(params)
        ret = self.api_request(check_login_url)
        code_string =  ret["data"]["codeString"]
        
        if code_string:
            logger.debug("Login check require verifycode")
            verifycode = self.get_verifycode(code_string)
        else:    
            verifycode = ""
            
        # try to login    
        login_params = dict(staticpage="http://pan.baidu.com/res/static/thirdparty/pass_v3_jump.html",
                            charset="utf-8",
                            token=token,
                            tpl="netdisk",
                            tt=utils.timestamp(),
                            codestring=code_string,
                            isPhone="false",
                            safeflg=0,
                            u="http://pan.baidu.com/",
                            username=self.username,
                            password=self.password,
                            verifycode=verifycode,
                            mem_pass="on",
                            )    
        login_url = "https://passport.baidu.com/v2/api/?login"
        html = self.curl.request(login_url, data=login_params, method="POST")
        url = re.findall(r"encodeURI\('(.*?)'\)", html)[0]
        self.curl.request(url)
        return self.check_login(stage + 1)
    
    def api_request(self, url, method="GET", extra_data=dict(), retry_limit=2, encoding=None, **params):
        ret = None
        data = {}
        data.update(extra_data)
        data.update(params)
        for key in data:
            if callable(data[key]):
                data[key] = data[key]()
            if isinstance(data[key], (list, tuple, set)):
                data[key] = ",".join(map(str, list(data[key])))
            if isinstance(data[key], unicode):    
                data[key] = data[key].encode("utf-8")
                
        start = time.time()        
        ret = self.curl.request(url, data, method)
        if ret == None:
            if retry_limit == 0:
                logger.debug("API request error: url=%s" % self.curl.url)
                return dict()
            else:
                retry_limit -= 1
                return self.api_request(url, method, extra_data, retry_limit, **params)
            
        if encoding != None:    
            ret = ret.decode(encoding)
        data = parser_json(ret)       
        logger.debug("API response %s: TT=%.3fs", self.curl.url,  time.time() - start )
        return data
    
    def _bduss(self):
        if self.__bduss != None:
            return self.__bduss
        
        cj = cookielib.MozillaCookieJar(self.cookie_file)
        cj.load()
        for c in cj:
            if c.name == 'BDUSS' and c.domain.endswith('.baidu.com'):
                self.__bduss = c.value
                return c.value
        raise RuntimeError('BDUSS cookie not found')

    
    def _wget_analytics(self, method='http'):
        params = dict(_lsid = utils.timestamp(),
                      _lsix = 1,
                      page = 1,
                      clienttype = 0,
                      type = "offlinedownloadtaskmethod",
                      method = method)
        ret =  self.api_request("http://pan.baidu.com/api/analytics", extra_data=params)
        if ret['errno'] != 0:
            raise RuntimeError("method not supported")
        
    def wget(self, url, save_to="/"):    
        self._wget_analytics()
        params = dict(method = "add_task",
                      app_id = 250528,
                      BDUSS = self._bduss(),
                      source_url = url,
                      save_path = save_to)
        ret = self.api_request("http://pan.baidu.com/rest/2.0/services/cloud_dl",
                               method="POST", extra_data=params)
        print ret
        return ret['task_id']
    
    def status(self, task_id):
        taskids = ','.join(task_id) if isinstance(task_id, (list, tuple)) else str(task_id)
        params = dict(method = 'query_task',
                      app_id = 250528,
                      BDUSS = self._bduss(),
                      task_ids = taskids,
                      op_type = 1,
                      t = utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/rest/2.0/services/cloud_dl",
                               method="GET", extra_data=params)
        return ret
    
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
        params = dict(method='list_task',
                     app_id=250528,
                     BDUSS=self._bduss(),
                     need_task_info=1,
                     status=255,
                     t=utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/rest/2.0/services/cloud_dl",
                               method="GET", extra_data=params)
        return ret["task_info"]
    
    def _list(self, dir="/", page=1, initialCall=True):
        # None for error
        params = dict(channel='chunlei',
                      clienttype=0,
                      web=1,
                      num=100,
                      t=utils.timestamp(),
                      page=page,
                      dir=dir,
                      _=utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/api/list", 
                               extra_data=params)
        files = ret['list']
        if len(files) == 100:
            files.extend(self._list(dir, page=page+1, initialCall=False))
        return files
    
    def list(self, dir="/"):
        files = self._list(dir)
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
        
        ret = self.api_request("http://pan.baidu.com/api/filemanager?"
                               "channel=chunlei&clienttype=0&web=1&opera=delete",
                               method="POST", extra_data=params)
        return ret
        
    def rename(self, path, newname):
        newname = os.path.basename(newname)
        params = dict(filelist=json.dumps([dict(path=path,
                                                newname=newname)]))
        ret = self.api_request("http://pan.baidu.com/api/filemanager?"
                              "channel=chunlei&clienttype=0&web=1&opera=rename",
                               method="POST", extra_data=params)
        return ret

    def move(self, src, dst, newname):
        params = dict(filelist=json.dumps([dict(path=src,
                                                dest=dst,
                                                newname=newname or os.path.basename(src))]))
        ret = self.api_request("http://pan.baidu.com/api/filemanager?"
                               "channel=chunlei&clienttype=0&web=1&opera=move",
                               method="POST", extra_data=params)
        return ret

    def quota(self):
        params = dict(channel="chunlei",
                      clienttype=0,
                      web=1,
                      t=utils.timestamp())
        ret = self.api_request("http://pan.baidu.com/api/quota", extra_data=params)
        return ret
            
    def _create(self, path, blocks, size, isdir=0):
        params = dict(path = path,
                      isdir = isdir,
                      size = size,
                      block_list = json.dumps(blocks),
                      method = 'post')
        ret = self.api_request("http://pan.baidu.com/api/create?a=commit&channel=chunlei&clienttype=0&web=1",
                               method="POST", extra_data=params)
        return ret

    def upload(self, filepath, upload_to="/"):
        params = dict(method='upload',
                      type='tmpfile',
                      app_id=250528,
                      BDUSS=self._bduss())
        files = [("file", (pycurl.FORM_FILE, filepath)),]
        resp = self.curl.request("http://c.pcs.baidu.com/rest/2.0/pcs/file?" + \
                                   urllib.urlencode(params),
                                method="UPLOAD", data=files)
        ret = parser_json(resp)
        size = os.path.getsize(filepath)
        return self._create(os.path.join(upload_to, os.path.basename(filepath)),
                            [ret['md5']], size)

    def mkdir(self, path):
        return self._create(path, [], "", isdir=1)
