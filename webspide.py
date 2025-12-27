import os, time, random, re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import html2text
import json
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options


# ---------- 配置区 ----------
EDGE_DRIVER_PATH = r"   "  # 修改为你的 msedgedriver 路径
USER_ANSWERS_URL = "    "  # 替换为爬取主页

OUTPUT_DIR = Path("   ")   # 输出目录
IMAGES_DIR = OUTPUT_DIR / "images"

# ---------- 工具函数 ----------
def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(s):
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    return s.strip()[:200]

def download_image(url, referer=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            ext = os.path.splitext(urlparse(url).path)[1] or ".jpg"
            fname = sanitize_filename(os.path.basename(urlparse(url).path)) or f"img_{int(time.time()*1000)}"
            out_path = IMAGES_DIR / f"{fname}{ext}"
            with open(out_path, "wb") as f:
                f.write(resp.content)
            return out_path.name
    except Exception:
        pass
    return None

def convert_html_to_markdown(html_fragment):
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    return h.handle(html_fragment)

COOKIES_FILE = OUTPUT_DIR / "cookies.json"

def save_cookies(driver):
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f)
    print(f"Cookies 已保存到 {COOKIES_FILE}")

def load_cookies(driver, url="   "): #输入url
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        driver.get(url)
        for cookie in cookies:
            # 只保留 Selenium 支持的字段
            c = {
                "name": cookie.get("name"),
                "value": cookie.get("value"),
                "domain": cookie.get("domain"),
                "path": cookie.get("path", "/")
            }
            try:
                driver.add_cookie(c)
            except Exception as e:
                print("跳过无效 Cookie:", c, e)
        driver.refresh()
        print("已加载本地 Cookies，自动登录成功")
        return True
    return False



def init_driver():
    opts = Options()
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1200,900")
    service = Service(EDGE_DRIVER_PATH)
    driver = webdriver.Edge(service=service, options=opts)
    driver.set_page_load_timeout(30)
    return driver

def scroll_to_bottom(driver, max_scrolls=200, pause=2):
    # 等待页面加载出 body
    driver.implicitly_wait(10)
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
    except Exception:
        print("页面未加载出 body，可能跳转到登录页或出错")
        return
    
    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause + random.random())
        try:
            new_height = driver.execute_script("return document.body.scrollHeight")
        except Exception:
            break
        if new_height == last_height:
            break
        last_height = new_height

from urllib.parse import urljoin

def collect_answer_links(driver, url,max_pages=10):
    links = []
    for page in range(1,max_pages+1):
        pageurl = f"{url}?page={page}"
        driver.get(pageurl)
        scroll_to_bottom(driver)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for a in soup.select("a[href*='/answer/']"):
            href = a.get("href")
            if href:
                full_url = urljoin("  ", href) #爬取网站
                links.append(full_url)
    print("抓到详情页数量:", len(links))
    return list(set(links))

def process_answer(driver, url):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
      
    # 更精确的选择器
    content = soup.select_one(".RichContent-inner") or soup.select_one(".RichText")
    if not content:
        print("未找到回答正文:", url)
        return None, None

    # 下载图片并替换链接
    for img in content.find_all("img"):
        src = img.get("src")
        if src:
            local_name = download_image(src, referer=url)
            if local_name:
                img["src"] = f"./images/{local_name}"

    title = sanitize_filename(driver.title)
    md_body = convert_html_to_markdown(str(content))
    meta = f"# {title}\n\n> 来源: {url}\n\n---\n\n"
    out_file = OUTPUT_DIR / f"{title}.md"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(meta + md_body)

    print(f"已保存: {out_file}")
    return out_file.name, time.time()


def generate_index(files):
    # 按时间排序（最新在最上面）
    files.sort(key=lambda x: x[1], reverse=True)
    readme_path = OUTPUT_DIR / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# 目录索引\n\n")
        for fname, _ in files:
            f.write(f"- [{fname}]({fname})\n")
    print(f"目录索引已生成: {readme_path}")

def main():
    ensure_dirs()
    driver = init_driver()
    saved_files = []
    try:
        # 自动登录逻辑
        if not load_cookies(driver):
            driver.get("  ") #爬取网站登录页面
            print("请登录，等待 3秒...")
            time.sleep(3)
            save_cookies(driver)
        driver.get(USER_ANSWERS_URL)
        # 登录完成后再去收集
        links = collect_answer_links(driver, USER_ANSWERS_URL,max_pages=10)
        print(f"共收集到 {len(links)} 个链接")
        for url in links:
            try:
                fname, ts = process_answer(driver, url)
                saved_files.append((fname, ts))
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"抓取 {url} 出错: {e}")
        generate_index(saved_files)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
