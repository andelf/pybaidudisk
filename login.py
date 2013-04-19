#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

import urllib
import urllib2
import cookielib

import atexit

import time
import platform

# fix 32bit time_t.
if platform.architecture()[0].startswith('32'):
    old_gmtime = time.gmtime
    def gmtime(t):
        if t > 2000000000:
            t = 2000000000
        return old_gmtime(t)
    time.gmtime = gmtime

def strip_url(u):
    return u.replace('&amp;', '&')

__cookies__ = os.path.join(os.path.dirname(__file__), 'cookies.txt')

cj = cookielib.LWPCookieJar(__cookies__)
# cj.load()
atexit.register(lambda : cj.save())

cp = urllib2.HTTPCookieProcessor(cj)
opener = urllib2.build_opener(cp)
opener.addheaders = [
    ('User-agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/535.24 ' \
         '(KHTML, like Gecko) Chrome/19.0.1056.0 Safari/535.24'),]


html = opener.open("http://wapp.baidu.com/").read()
#print html
if "我的i贴吧" in html:
    print "login ok"
    raise SystemExit

login_url, = re.findall(r'<a href="([^ <>]*?)">登录', html)
print login_url
html = opener.open(login_url).read()
#print html
html = html.split("</form>")[1]


fields = re.findall(r'name="(\S+?)" .*?value="(.*?)"', html)
fields = dict(fields)

#fix
fields['aaa'] = '登陆'
fields['login_username'] = 'USERNAME'
fields['login_loginpass'] = 'PASSWORD'

data = urllib.urlencode(fields)

#print data

post_url, = re.findall(r'<form action="(.*?)"', html)
#print post_url
req = urllib2.Request(post_url, data)
html = opener.open(req).read()
if "请输入以下图片中的验证码" in html:
    print 'verify code needed, TODO later'
    raise SystemExit

refresh_url, = re.findall(r'<meta http-equiv="refresh" content="\d+;url=(.*?)"', html)
#print refresh_url

html = opener.open(refresh_url).read()

#print html
