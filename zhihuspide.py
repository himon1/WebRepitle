import requests
import time
import os
import re
from bs4 import BeautifulSoup
from pathlib import Path
import html2text

# ---------- 配置 ----------
OUTPUT_DIR = Path("D:/code/zhihu")
ANSWERS_DIR = OUTPUT_DIR / "answers_md"

def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()[:200]

# ---------- 获取回答列表 ----------
def fetch_answer_list(user_id, limit=20, cookies=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    if cookies:
        headers["cookie"] = cookies

    answers_meta = []
    offset = 0

    while True:
        url = f"https://www.zhihu.com/api/v4/members/{user_id}/answers?offset={offset}&limit={limit}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print("列表请求失败:", resp.status_code)
            break

        data = resp.json()
        items = data.get("data", [])
        if not items:
            break

        for item in items:
            ans_id = item.get("id")
            q_title = (item.get("question") or {}).get("title") or "未命名问题"
            answers_meta.append({"id": ans_id, "question": q_title})

        print(f"列表累计：{len(answers_meta)} 条")
        offset += limit
        time.sleep(0.8)

    return answers_meta

# ---------- 获取回答详情并转 Markdown ----------
def fetch_answer_detail(answer_id, cookies=None):
    headers = {"User-Agent": "Mozilla/5.0"}
    if cookies:
        headers["cookie"] = cookies

    url = f"https://www.zhihu.com/api/v4/answers/{answer_id}?include=content"
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"详情请求失败 {answer_id}:", resp.status_code)
        return ""

    data = resp.json()
    html = data.get("content") or data.get("excerpt") or ""
    if not html:
        return ""

    # 转 Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    md_text = h.handle(html)
    return md_text.strip()

# ---------- 保存 ----------
def save_answers_individual(items, folder=ANSWERS_DIR):
    os.makedirs(folder, exist_ok=True)
    saved = 0
    for it in items:
        title = sanitize_filename(it["question"])[:80]
        body = it.get("content", "").strip()
        if not body:
            body = "（正文未返回或为空）"

        path = os.path.join(folder, f"{title}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# 问题：{it['question']}\n\n")
            f.write(body + "\n")
        saved += 1
    print(f"已保存 {saved} 个回答到 {folder}")

# ---------- 主入口 ----------
def main():
    ensure_dirs()
    user_id = "lan-lan-wan"  # 例如 people/abc123/answers 中的 abc123
    cookies = "expire_in=15552000;assva5=U2FsdGVkX18vVOcfzgONJMv0sJcAP7CeNG5vPRpzUqxRKmerPZ7bnCXxCNJ32rg5liy3c8/TWOXRBMFgMg8H/g==;q_c1=f0a11b4d6b394390ad741bbf29f46bc0|1756293203000|1756293203000;ref_source=people;z_c0=2|1:0|10:1766501261|4:z_c0|92:Mi4xLVhES1JnQUFBQUR1bEZPMGctTDZHaGNBQUFCZ0FsVk5pdmszYWdDbFE2SFVDdEUtV3k4TWNTcGlxZk8zTGw0QWxR|ada7bf4f79f027ca1ea42d5a5620477a0dfb9e5eac13fa28476d45eea596eedf;osd=Ul0UBU_X8UHduru9Vkb3VMI7X0ZN5sILvNn97BuBjhWQ6ObLZm65C7K7ur5Tx_uDi5_Etc0S4lVHpm25d7w0MDI=;Hm_lpvt_98beee57fd2ef70ccdd5ca52b9740c49=1766835062;HMACCOUNT=DACB8B61C726DD20;gdxidpyhxdE=YTh3ITQ96aUYvgBzKaZmTE4N4Ekcxio87R%2FBEv3wBDe%2FNEciPi2JsWu12k%2BlVrC2tIjxEvy2VNG3pEjt2kxblVfaNE7tz2TbVgkl%2Bmc2N0XobEGj6wObqq5yezkhR5KrB%2BmTmZIjcEroW41BERB0BliN2cA%5CWhHLr7wkMQbN%2F%5CJng0w9%3A1766502021978;_xsrf=W1a1Bi5qu6ZqMm9pL4BKCWN7T8uJqNtG;BEC=7aabe613cb4d97a48eb82ad02e0db63f;captcha_session_v2=2|1:0|10:1766501252|18:captcha_session_v2|88:dGJMR1Zacjkra2IvUWN2aDBlYi83ZWhaNWdaa0FXcEFNSm5YWmMwcW9NaXZ6SkI3SU5iQjJTQ2tXd2d5d1pFUg==|4b476e5cea114d3b8054ac1d888d1002e843dec7a1ca01ca6fe7f79c4a2b2b60;JOID=U1AdBUrW_Ejdv7qwX0byVc8yX0NM68sLudjw5RuEjxiZ6OPKa2e5DrO2s75WxvaKi5rFuMQS51RKr228drE9MDc=;cmci9xde=U2FsdGVkX19bZ3a70UbFnHxaW1C37aPx34B68/bvU8DPjjjTw7aqUg9vzlL3AHdmY+PVdqYY4rg4b3jjXwYDUg==;__snaker__id=BWhmjhiEvMXV62UY;__zse_ck=005_kG0TRwKapkJqVFiLP5hChzFtcsoDEEnZyBs7lX1cajsDcjrG/1AYlfmUn/ViDm0tthqdHgliv1Y/cV3v9L6XDmRlhZSuJi7W82lP6Wt/Mu2Vy4uuA7Yk/Xv=UcDqU7yz-JdptNI+5+0pNPZBBbo08OjZX1Y0XGPa5cT2Ae1RwJEtZ8ayvIvjbC8vNwO7anQ4a2uaNgKmYw19RVPrczC6xocK2T8MZ8AuyKY0yeasYsepzCO6Pi8wIHOzrYUNVkejAN/XQgl2HGJr6JSFbUE3mHw==;_zap=ddbf7eaf-0359-48d1-a59d-6c0ec33d18f8;assva6=U2FsdGVkX1835tlJax4PaS1+wrGAIbb/8JzOlyNd60Q=;crystal=U2FsdGVkX1+cDg8kwjqTr1dtjPfruPDhFJAUpLhOaQ67uFvQoCWBIP+VzM8UQIHAnr3gBY7B2ox19e5dYaodDbVw3GdnirYbHhc1S7Q/kIfZg/CnQzZY2COT1iWMwSx7JxGPL1CgAx+v2XFt43/JI3I9svBt1cPQ2OVVvbieUk2ojzdVjJcgYBQMvfR2e6R+fyxlawTYdNR9KRJ8xVRnAXuw0eGRL+/pW3qZ0dwOLWvHGaMH68dTGBndVrzT2d8q;d_c0=7pRTtIPi-hqPTuF3aVM6RVsjgLOZW2pyY7k=|1756293194;DATE=1756293177395;Hm_lvt_98beee57fd2ef70ccdd5ca52b9740c49=1765089062;o_act=login;pmck9xge=U2FsdGVkX19k0mFILYL6G8tcF6cZJ7zB8rVTRpaTGAE=;SESSIONID=47McgCUJRzPJPYs445dNnXGAcnEpFYUMpGNYAzv5rBY;vmce9xdq=U2FsdGVkX1+36cS0vvrlCijB7xXBoSXkdmGiIXKcn36u3flHrWxHoslaTPn5DoPFedd4aqWWWNNMnvVrc0KQg+PZ+ubxUaVbCiE+GM28M2LBkJFBVHt25jQwCxIfqhyRV0JPMcqgkSv6k0c1MfztD/cmT0tuqmiS31YlC/GUNqU="

    metas = fetch_answer_list(user_id, limit=20, cookies=cookies)
    print("列表总数：", len(metas))

    results = []
    for i, meta in enumerate(metas, 1):
        md_content = fetch_answer_detail(meta["id"], cookies=cookies)
        results.append({"question": meta["question"], "content": md_content})
        if i % 20 == 0:
            print(f"详情进度：{i}/{len(metas)}")
        time.sleep(0.6)

    save_answers_individual(results, ANSWERS_DIR)
    print("完成，总计：", len(results))

if __name__ == "__main__":
    main()
