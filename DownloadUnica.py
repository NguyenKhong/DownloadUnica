# -*- coding: utf-8 -*-

import sys
import os

if __package__ is None and not hasattr(sys, 'frozen'):
    # direct call of __main__.py
    # print ("import new")
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

# input(">>>>> ")
import requests
import re
from bs4 import BeautifulSoup
import time
import timeit
from urllib.parse import urljoin, urlparse
import unicodedata
import datetime
import ntpath
import struct
import shutil
import threading
import urllib.request, urllib.parse, urllib.error
import logging
import ctypes
import json
import queue
from var_dump import var_dump
from streamlink_cli.main import main as streamlink_cli_main
import update
import version
import argparse

os.environ['HTTPSVERIFY'] = '0'

g_session = None

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:44.0) Gecko/20100101 Firefox/44.0'
BASE_URL = 'https://unica.vn/'
LOGIN_URL = 'https://id.unica.vn/login'
COURSES_URL = 'https://unica.vn/dashboard/user/course'
PLUGIN_DIR = ""
if getattr(sys, 'frozen', False):
    FFMPEG_LOCATION = os.path.join(sys._MEIPASS, 'ffmpeg', 'ffmpeg.exe')
    PLUGIN_DIR = os.path.join(sys._MEIPASS, 'plugins')
else:
    FFMPEG_LOCATION = os.path.join(os.getcwd(), 'ffmpeg', 'ffmpeg.exe')

# std_headers['User-Agent'] = USER_AGENT

g_CurrentDir = "d:\\"#os.getcwd()
kernel32 = ctypes.windll.kernel32

logger = logging.getLogger("DownloadUnica")

stdout_logger = logging.StreamHandler()
file_logger = logging.FileHandler("DownloadUnica.log", 'w', 'utf-8')
formatter = logging.Formatter('%(asctime)s %(funcName)s %(levelname)s: %(message)s')
stdout_logger.setFormatter(formatter)
file_logger.setFormatter(formatter)

logger.addHandler(stdout_logger)
logger.addHandler(file_logger)
logger.setLevel(logging.INFO)

def NoAccentVietnamese(s):
    s = s.encode().decode('utf-8')
    s = re.sub('Đ', 'D', s)
    s = re.sub('đ', 'd', s)
    return unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore')

def removeCharacters(value, deletechars = '<>:"/\|?*'):
    value = str(value)
    for c in deletechars:
        value = value.replace(c,'')
    return value

def GetFileNameFromUrl(url):
    urlParsed = urlparse(urllib.parse.unquote(url))
    fileName = os.path.basename(urlParsed.path).encode('utf-8')
    return removeCharacters(fileName)

def pathLeaf(path):
    '''
    Name..........: pathLeaf
    Description...: get file name from full path
    Parameters....: path - string. Full path
    Return values.: string file name
    Author........: None
    '''
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

def Request(url, method = 'GET', session = None, **kwargs):
  
    if kwargs.get('headers') is None:
        kwargs['headers'] = {'User-Agent' : USER_AGENT}
    elif kwargs.get('headers').get('User-Agent') is None:
        kwargs['headers']['User-Agent'] = USER_AGENT    
   
    method = method.lower()
    if session:
        func = getattr(session, method)
    else:
        func = getattr(requests, method)
    try:
        response = func(url, **kwargs)
    except Exception as e:
        logger.critical("Error: %s - url: %s", e, url)
        return None
    
    if response.status_code != 200:
        logger.critical('Error: %s - url: %s', response.content, url)
        return None
    return response

def Login(user, password):
    
    r = Request(LOGIN_URL, session = g_session, headers = {'referer' : BASE_URL})

    _csrf = re.findall(r'<input id="form-token" type="hidden" name="_csrf" value="(.*?)"\/>', r.text)
    if not _csrf:
        logger.critical("Dang nhap loi vui long lien he nha phat trien")
        sys.exit(1)

    payload = { 'email' : user,
                'pass': password,
                '_csrf' : _csrf[0],
        }
    headers = { 'origin' : '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(LOGIN_URL)) ,
                'referer' : LOGIN_URL
        }
    r = Request(LOGIN_URL, 'POST', data = payload, headers = headers, session = g_session)  

    error = re.findall(r'class="alert\salert-danger\salert-dismissable\scol-md-12">\s+<a href="#"\sclass="close"\sdata-dismiss="alert"\saria-label="close">×<\/a>\s+<strong>\s+<center>(.*?)<br\/>', r.text, re.DOTALL)
    if error:
        logger.critical("Dang nhap loi: %s" % str(error[0]))
        sys.exit(1)
    return True

def GetCourses():
    
    r = Request(COURSES_URL, session = g_session)
    soup = BeautifulSoup(r.content, 'html5lib')
    courses = soup.findAll('div', {'class': 'ugb-lg-box'})
    if courses == []:
        logger.warning("Loi Phan tich khoa hoc")
        return []

    UrlCourses = []
    for course in courses:
        name = course.div.p
        if not name:
            logger.warning("Loi Phan tich tieu de khoa hoc")
            return []
        url = course.find('div', {'class' : 'ugb-block-txt'}).a['href']
        name = removeCharacters(name.text)
        UrlCourses.append({'url' : urljoin(COURSES_URL, url), 'title' : name.strip()})

    return UrlCourses

def GetLessions(url):
    r = Request(url, session = g_session)
    soup = BeautifulSoup(r.content, 'html5lib')

    # Menu = soup.find('div', {'class' : 'menu'})
    
    # buttonBuy = soup.findAll('a', {'class' : 'btn-red btn-buy'})
    # if buttonBuy:
    #     print "Khoa hoc nay chua mua."
    #     return [] 
    # if not Menu:
    #     logger.warning('Loi Khong the phan tich toan bo bai giang nay')
    #     return []
    # if not Menu.a.get('href'):
    #     logger.warning('Loi Thieu url de phan tich bai giang')
    #     return []

    # url = urljoin(url, Menu.a.get('href'))
    # r = Request(url, session = g_session)
    # soup = BeautifulSoup(r.content, 'html5lib') 
    Lessions = soup.findAll('div', {'class' : 'col-xs-9 col-md-10'})
    if not Lessions:
        logger.warning('Loi Khong the lay danh sach bai giang')
        return []
    UrlLessions = []
    for lession in Lessions:
        tag_a = lession.div.a
        if not tag_a:
            logger.warning("Loi Phan tich Ten bai giang")
            return []
        UrlLessions.append({'url' : urljoin(url, tag_a.get('href')), 'title' : removeCharacters(tag_a.text).strip()})
    return UrlLessions 

def GetVideoAndDocument(url, serverOption = 1, isGetLinkDocument = True):
    headers = {'origin' : BASE_URL, 'referer' : url}
    infoMedia = {}
    servers = [
        url + "?server=vn",
        url + "?server=qt"
    ]
    

    r = Request(servers[serverOption-1], headers = headers, session = g_session)
    # url_videos = re.findall(r'{"file":"(.*?)","label":"(\d+)p', r.content)
    # url_videos = re.findall(r'{"file":"([^\[\{\"]*?)","label":"', r.text)
    url_videos = re.findall(r'src: "(.*?)".*?label: "(\d+)"', r.text, re.DOTALL)

    if url_videos:
        max_resolution = -1
        for url, resolution in url_videos:
            resolution = int(resolution)
            if resolution > max_resolution:
                max_resolution = resolution
                infoMedia['url'] = url.replace("\\/", "/")
                
        infoMedia['headers'] = {'origin' : BASE_URL, 'referer' : url}
        infoMedia['protocol'] = 'm3u8'
    
    else:
        # r = Request(url_server_vn, headers = headers, session = g_session)
        url_videos = re.findall(r'src: "(.*?)",', r.text)
        if url_videos:
            infoMedia['url'] = url_videos[-1].replace("\\/", "/")
            infoMedia['headers'] = {'origin' : BASE_URL, 'referer' : url}
            infoMedia['protocol'] = 'm3u8'

    if infoMedia == {}:
        logger.warning('Loi lay thong tin tai video')
    urlDocuments = []
    if isGetLinkDocument:
        soup = BeautifulSoup(r.content, 'html5lib')
        documentDownloads = soup.find('div', {'id': 'fileLession'}).findAll('div', {'class': 'uom-file-ulti'})
        # if documentDownload.text.find(u'Tài liệu của bài học') != -1:
        for i in documentDownloads:
            urlDocuments.append(urljoin(url, i.a.get('href'))) 
    return infoMedia, urlDocuments 

def DownloadFile(url, pathLocal, isSession = False, headers = {}):
    r = None
    fileName = ""
    try:
        session = None
        if isSession: session = g_session
        r = Request(url, session = session, stream = True, headers = headers)
        fileAttach = r.headers.get('Content-disposition', '')
        if 'attachment' in fileAttach:
            fileName = fileAttach[22:-1]
        else:
            fileName = GetFileNameFromUrl(url)
        
        fullPath = os.path.join(pathLocal, removeCharacters(fileName))
        if os.path.exists(fullPath):
            return True
        with open(fullPath, 'wb') as f:
            for chunk in r.iter_content(5242880):
                f.write(chunk)
        print(fileName)
    except Exception as e:
        logger.warning("Loi: %s - url: %s", e, url)
        return False
    # finally:
    #     if not r:
    #         r.close()
    return True

def TryDownloadDocument(urls, pathLocal):
    for url in urls:
        for i in range(5):
            if DownloadFile(url, pathLocal, isSession=True):
                break
            time.sleep(1)

def DownloadCourses():
    print("")
    email = input(' Email: ')
    password = input(' Password: ')
    if (email == "") or (password == ""):
        print ("email hoac password khong co")
        return
    
    if not Login(email, password):
        return

    print(30*"=")
    if args.bypass_buy:
        url = input('Nhap url khoa hoc: ')
        CoursesDownload = getCourseNoBuy(url)
    else:
        Courses = GetCourses()
        if not Courses: return

        print("Danh sach cac khoa hoc: ")
        i = 1
        for course in Courses:
            print("\t %d. %s" % (i, course['title']))
            i += 1

        print("\n  Lua chon tai ve cac khoa hoc")
        print("  Vd: 1, 2 hoac 1-5, 7")
        print("  Mac dinh la tai ve het\n")

        rawOption = input('(%s)$: ' % email)
        CoursesDownload = ParseOption(Courses, rawOption)

    if not CoursesDownload: return

    try:
        print ("Danh sach server tai video: \n\t1 viet nam\n\t2 quoc te")
        serverOption = input('Chon server download [1]: ')
        if serverOption == "":
            serverOption = 1
        serverOption = int(serverOption)
        if serverOption != 1 and serverOption != 2:
            print (">>> Xin vui long nhap dung so server")
            return
    except ValueError:
        print(">>> Nhap so")
        return
    
    try:
        NumOfThread = input('So luong download [5]: ')
        if NumOfThread == "":
            NumOfThread = 5
        NumOfThread = int(NumOfThread)
    except ValueError:
        print(">>> Nhap so")
        return

    listPathDirLessions = []
    DirDownload = os.path.join(g_CurrentDir, "DOWNLOAD")
    if not os.path.exists(DirDownload): os.mkdir(DirDownload)
    print("")
    print(30*"=")
    iCourses = 0
    lenCourses = len(CoursesDownload)
    for course in CoursesDownload:
        print(course['title'])
        pathDirCourse = os.path.join(DirDownload, removeCharacters(course['title'], '.<>:"/\|?*\r\n'))
        if not os.path.exists(pathDirCourse): os.mkdir(pathDirCourse)
        pathDirComplete = os.path.join(pathDirCourse, "complete")
        if not os.path.exists(pathDirComplete): os.mkdir(pathDirComplete)
        DirDocuments = os.path.join(pathDirComplete, "Documents")
        if not os.path.exists(DirDocuments): os.mkdir(DirDocuments)
        Lessions = GetLessions(course['url'])
        iLessions = 1
        lenLessions = len(Lessions)
        for Lession in Lessions:
            print(Lession['title'])
            
            lessionTitleClean = removeCharacters(Lession['title'], '.<>:"/\|?*\r\n')

            infoMedia, urlDocuments = GetVideoAndDocument(Lession['url'], serverOption)
            
            if not infoMedia: continue

            threadDownloadDocument = threading.Thread(target = TryDownloadDocument, args = (urlDocuments, DirDocuments))
            threadDownloadDocument.setDaemon(False)
            threadDownloadDocument.start()

            pathFileOutput = os.path.join(pathDirComplete, lessionTitleClean + ".mp4")
            if not os.path.exists(pathFileOutput):
                options = [
                    # '--loglevel',
                    # 'debug',
                    '--ringbuffer-size',
                    '64M',
                    '--ffmpeg-ffmpeg',
                    FFMPEG_LOCATION,
                    # '--output',
                    # pathFileOutput,
                    '--player-no-close',
                    '--player',
                    FFMPEG_LOCATION,
                    '-a',
                    '-i {filename} -y -c copy -bsf:a aac_adtstoasc -metadata "comment=Download_Unica (^v^)" "%s"' % pathFileOutput,
                    '--fifo',
                    '--hls-segment-threads',
                    str(NumOfThread),
                    infoMedia['url'],
                    'best'
                ]
                if PLUGIN_DIR:
                    options.append('--plugin-dirs')
                    options.append(PLUGIN_DIR)

                infoMedia["headers"].update({"User-Agent": USER_AGENT})
                
                for k, v in infoMedia["headers"].items():
                    options.append("--http-header")
                    options.append("%s=%s" % (k, v))
                streamlink_cli_main(options)

            percentLessions = iLessions*1.0/lenLessions*100.0
            message = "Total: %.2f%% - %s: %.2f%%" % (percentLessions/lenCourses + iCourses*1.0/lenCourses*100.0, course['title'], percentLessions)
            kernel32.SetConsoleTitleW(ctypes.c_wchar_p(message))
            
            iLessions += 1
            print(40*"*")
        
        print(50*"=")
        iCourses += 1
        message = "Total: %.2f%%" % (iCourses*1.0/lenCourses*100.0)
        kernel32.SetConsoleTitleW(ctypes.c_wchar_p(message))        

def DonwloadLessions():
    print("")
    email = input(' Email: ')
    password = input(' Password: ')
    if (email == "") or (password == ""):
        logger.info("email hoac password khong co")
        return

    if not Login(email, password): return

    print(30*"=")
    if args.bypass_buy:
        url = input('Nhap url khoa hoc: ')
        Courses = getCourseNoBuy(url)
    else:
        Courses = GetCourses()

    if not Courses: return

    print(" Danh sach cac khoa hoc: ")
    i = 1
    for course in Courses:
        print("\t %d. %s" % (i, course['title']))
        i += 1

    print("\n Lua chon tai ve 1 khoa hoc")

    rawOption = input(' (%s)$: ' % email)
    try:
        lenCourses = len(Courses)
        index = int(rawOption) - 1
        if index > lenCourses - 1:
            index = lenCourses - 1
        if index < 0:
            index = 0
        course = Courses[index]
    except ValueError:
        print(" Lam on nhap SO")
        return

    DirDownload = os.path.join(g_CurrentDir, "DOWNLOAD")
    if not os.path.exists(DirDownload): os.mkdir(DirDownload)
    print(30*"=")
    print("")
    print(course['title'])
    pathDirCourse = os.path.join(DirDownload, removeCharacters(course['title'], '.<>:"/\|?*\r\n'))
    if not os.path.exists(pathDirCourse): os.mkdir(pathDirCourse)
    pathDirComplete = os.path.join(pathDirCourse, "complete")
    if not os.path.exists(pathDirComplete): os.mkdir(pathDirComplete)
    DirDocuments = os.path.join(pathDirComplete, "Documents")
    if not os.path.exists(DirDocuments): os.mkdir(DirDocuments)
    Lessions = GetLessions(course['url'])
    if not Lessions: return
    print("Danh sach cac bai giang: ")
    i = 1
    for Lession in Lessions:
        print("\t %d. %s" % (i, Lession['title']))
        i += 1

    print("\n  Lua chon tai ve cac bai giang")
    print("  Vd: 1, 2 hoac 1-5, 7")
    print("  Mac dinh la tai ve het\n")

    rawOption = input('(%s)$: ' % email)
    LessionsDownload = ParseOption(Lessions, rawOption)
    if not LessionsDownload: return

    try:
        print ("Danh sach server tai video: \n\t1 viet nam\n\t2 quoc te")
        serverOption = input('Chon server download [1]: ')
        if serverOption == "":
            serverOption = 1
        serverOption = int(serverOption)
        if serverOption != 1 and serverOption != 2:
            print (">>> Xin vui long nhap dung so server")
            return
    except ValueError:
        print(">>> Nhap so")
        return

    try:
        NumOfThread = input(' So luong download cung luc [5]: ')
        if NumOfThread == "":
            NumOfThread = 5
        NumOfThread = int(NumOfThread)
    except ValueError:
        print(">>> Nhap so")
        return

    for Lession in LessionsDownload:
        print(Lession['title'])
        
        lessionTitleClean = removeCharacters(Lession['title'], '.<>:"/\|?*\r\n')

        infoMedia, urlDocuments = GetVideoAndDocument(Lession['url'], serverOption)
        
        if not infoMedia: continue

        threadDownloadDocument = threading.Thread(target = TryDownloadDocument, args = (urlDocuments, DirDocuments))
        threadDownloadDocument.setDaemon(False)
        threadDownloadDocument.start()

        pathFileOutput = os.path.join(pathDirComplete, lessionTitleClean + ".mp4")
        if not os.path.exists(pathFileOutput):
            options = [
                '--loglevel',
                'debug',
                '--ringbuffer-size',
                '64M',
                '--ffmpeg-ffmpeg',
                FFMPEG_LOCATION,
                # '--output',
                # pathFileOutput,
                '--player-no-close',
                '--player',
                FFMPEG_LOCATION,
                '-a',
                '-i {filename} -y -c copy -bsf:a aac_adtstoasc -metadata "comment=Download_Unica (^v^)" "%s"' % pathFileOutput,
                '--fifo',
                '--hls-segment-threads',
                str(NumOfThread),
                infoMedia['url'],
                'best'
            ]
            if PLUGIN_DIR:
                    options.append('--plugin-dirs')
                    options.append(PLUGIN_DIR)
            infoMedia["headers"].update({"User-Agent": USER_AGENT})
            
            for k, v in infoMedia["headers"].items():
                options.append("--http-header")
                options.append("%s=%s" % (k, v))
            streamlink_cli_main(options)

        print(50*"=")

def ParseOption(listOption, rawOption):
    
    listOptionDownload = listOption
    if rawOption == "": return listOptionDownload
    try:
        listOptionDownload = []
        option = rawOption.split(",")
        lenCourses = len(listOption)
        for i in option:
            if i.find("-") != -1:
                c = i.split("-")
                c = list(map(int, c))
                c[0] -= 1
                if c[0] < 0:
                    c[0] = 0
                listOptionDownload += listOption[c[0]:c[1]]
            else:
                index = int(i) - 1
                if index > lenCourses - 1:
                    index = lenCourses - 1
                if index < 0:
                    index = 0
                listOptionDownload.append(listOption[index])
        return list(listOptionDownload)
    except ValueError:
        print(">>> Lam on nhap so.")
        return None

def getCourseNoBuy(url):
    r = Request(url, session = g_session)
    result = re.search(r'"name": "(?P<title>.*?)".*?"sku": "(?P<id>\d+)"', r.text, re.DOTALL)
    
    if result:
        return [{
                'title': str(result.group('title')).strip(),
                'url': "https://unica.vn/learn/%s/overview" % result.group('id'),
            }
        ]
    return []

def build_args():
    global args
    description = """\
Please enter -n or --no-update to disable process update."""
    parser = argparse.ArgumentParser(description = description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-n', '--no-update', action = 'store_false', dest="no_update", help = 'Disable update')

    description = """\
Please enter -b or --bypass-buy to bypass buy course."""
    parser = argparse.ArgumentParser(description = description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-b', '--bypass-buy', action = 'store_true', dest="bypass_buy", help = 'bypass buy course')
    args = parser.parse_args()
    return args

def menu():
    if getattr(sys, 'frozen', False):
        PATH_LOGO = os.path.join(sys._MEIPASS, 'logo', 'logo.txt')
    else:
        PATH_LOGO = os.path.join(os.getcwd(), 'logo', 'logo.txt')

    with open(PATH_LOGO, 'r') as f:
        for i in f:
            sys.stdout.write(i)
            time.sleep(0.07)
    print ("Version: %s" % version.VERSION)
    print("")
    print("\t0. Thoat")
    print("\t1. Tai cac khoa hoc")
    print("\t2. Tai cac bai giang con thieu")
    print("")

def main():  
    while (True):
        global g_session
        g_session = requests.Session()
        os.system('cls')
        menu()
        option = input("\t>> ")
        try:
            option = int(option)
        except ValueError:
            print("\n\t>> Nhap SO <<")
            continue
        if(option == 0):
            return
        elif(option == 1):
            DownloadCourses()
        elif(option == 2):
            DonwloadLessions()
        else:
            print("\n\t>> Khong co lua chon phu hop <<")
        g_session.close()
        input('\n\tNhan enter de tiep tuc...')

if __name__ == '__main__':
    # os.environ['HTTP_PROXY'] = "http://127.0.0.1:8888"
    # os.environ['HTTPS_PROXY'] = os.environ['HTTP_PROXY']

    args = build_args()
    # if args.no_update:
    #     update.CheckUpdate()
    try:
        main()
    except KeyboardInterrupt:
        print("CTRL-C break")

# nhhuayt@yahoo.com
# 09051990