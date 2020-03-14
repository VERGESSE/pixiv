import os
import shutil

from PIL import Image
from selenium import webdriver
import time
import requests
from lxml import etree
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Queue
import re

# 获取浏览器的数据，要先在自己的浏览器登陆一遍
chrome_path = r'C:\Users\administered\AppData\Local\Google\Chrome\User'
chrome_options = webdriver.ChromeOptions()
# 设置headless模式，无界面
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--user-data-dir="+chrome_path)
chrome_options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
chrome_options.add_argument('--disable-gpu')
# 设置不加载图片模式
# chrome_options.add_argument("blink-settings=imagesEnabled=false")
browser = webdriver.Chrome(executable_path="E:\Python\chromedriver.exe",
                          chrome_options=chrome_options)
browser.maximize_window()

work_executor = ThreadPoolExecutor(max_workers=1)
img_executor = ThreadPoolExecutor(max_workers=66)
path_queue = Queue()
all_task = []


# "https://www.pixiv.net/artworks/71767676"
def init_load(origin_path):
    print("正在初始化页面...")
    browser.get(origin_path)
    time.sleep(2)
    for i in range(1, 10):
        time.sleep(1)
        browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")
        try:
            login_button = browser.find_element_by_xpath("//*[@id='root']/div[3]/div/aside[2]/div/div[2]/button")
            login_button.click()
        except:
            continue
    print("页面初始化完成，开始爬取...")
    page = browser.page_source
    dom = etree.HTML(page)
    time.sleep(1)
    paths = dom.xpath("//aside//li/div/div[1]/div/a/@href")
    paths.insert(0, origin_path[21:])
    for path in paths:
        path_queue.put(path)


def init_img_load():
    while path_queue.empty():
        time.sleep(1)
    while not path_queue.empty():
        origin_path = path_queue.get()
        browser.get('https://www.pixiv.net'+origin_path)
        time.sleep(1)
        for i in range(1, 10):
            browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            time.sleep(1)
            try:
                login_button = browser.find_element_by_xpath("//*[@id='root']/div[3]/div/aside[2]/div/div[2]/button")
                login_button.click()
            except:
                continue

        time.sleep(1)
        # 清理一次垃圾图片
        img_filter("E:\Python\pixiv\pixiv_spider\images")

        page = browser.page_source
        dom = etree.HTML(page)
        time.sleep(1)
        ids = dom.xpath("//li/div/div/div/a/div/img/@src")
        nums = dom.xpath("//dd[@title='收藏']")[0].text
        # print(ids)
        for id in ids:

            img_url = id
            uri = re.findall("^.*?img/(.*?_p0).*?", img_url)[0]

            img_url = 'https://i.pximg.net/'+'img-original/img/'+uri+'.jpg'
            all_task.append(img_executor.submit(load_img, img_url))

            img_url = 'https://i.pximg.net/'+'img-original/img/'+uri+'.png'
            all_task.append(img_executor.submit(load_img, img_url))
            time.sleep(0.1)


def load_img(img_url):
    img_id = img_url[57:65]
    # print(img_id)
    fileName = "images/"+img_url.split('/')[-1]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "",
        "Connection": "keep-alive",
    }
    response = requests.get("https://www.pixiv.net/artworks/"+img_id, headers=headers)
    html = response.text
    num = re.findall('.*?bookmarkCount":(.*?),".*?', html)[0]
    if int(num) > 3000:
        print('正在爬取: '+img_url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "",
            "Connection": "keep-alive",
            'Referer': 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id='+img_id
        }
        response = requests.get(img_url, headers=headers)
        with open(fileName, 'wb') as f:
            f.write(response.content)


# "E:\Python\pixiv\pixiv_spider\images"
def img_filter(path):
    print("开始过滤清晰度不合格图片...")
    file_list = os.listdir(path)
    small_path = "E:\Python\pixiv\pixiv_spider\small"
    for file in file_list:
        pathTmp = os.path.join(path, file)
        small_path_tmp = os.path.join(small_path, file)
        filesize = os.path.getsize(pathTmp)
        if int(filesize) < 300000:
            os.remove(pathTmp)
            continue
        if int(filesize) < 1000000:
            shutil.move(pathTmp, small_path_tmp)
            continue
        img = Image.open(pathTmp)
        img_size = img.size
        img.close()
        minSize = min(img_size)
        if minSize < 1100:
            shutil.move(pathTmp, small_path_tmp)
            continue
        maxSize = max(img_size)
        if maxSize < 1900:
            shutil.move(pathTmp, small_path_tmp)
            continue


if __name__ == '__main__':
    print("输入P站初始页，本爬虫将爬取所有相关图片，并过滤清晰度(size > 1M, pixel > 1200, 收藏 > 3000)")
    origin_path = input("请输入你要爬取的初始页: \n")
    init_load(origin_path)

    result = work_executor.submit(init_img_load)
    result.result()
    time.sleep(60)
    img_filter("E:\Python\pixiv\pixiv_spider\images")
    browser.close()


# time.sleep(10)
# browser.close()
# https://i.pximg.net/c/360x360_70/img-master/img/2019/01/01/00/01/35/72414391_p0_square1200.jpg
# //*[@id="root"]/div[2]/div/aside[2]/div/section/div[2]/ul/li[1]/div/div[1]/div/a
# https://i.pximg.net/c/360x360_70/img-master/img/2019/12/04/22/31/16/78140180_p0_square1200.jpg