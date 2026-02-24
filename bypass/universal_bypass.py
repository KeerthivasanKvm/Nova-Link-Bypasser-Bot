"""
Universal Bypass
================
Handles all shorteners, file hosts, scrapers.
All requests go through proxy rotation to avoid IP blocks.
"""

import re
import time
import base64
import asyncio
from typing import Optional
from urllib.parse import urlparse, unquote, parse_qs

import requests
import cloudscraper
from bs4 import BeautifulSoup
from curl_cffi.requests import Session as CurlSession

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from bypass.proxy_manager import proxy_manager
from utils.logger import get_logger

logger = get_logger(__name__)

import os
GDTOT_CRYPT = os.environ.get("GDTOT_CRYPT",  "b0lDek5LSCt6ZjVRR2EwZnY4T1EvVndqeDRtbCtTWmMwcGNuKy8wYWpDaz0%3D")
DCRYPT      = os.environ.get("DRIVEFIRE_CRYPT", "")
KCRYPT      = os.environ.get("KOLOP_CRYPT",     "")
HCRYPT      = os.environ.get("HUBDRIVE_CRYPT",  "")
KATCRYPT    = os.environ.get("KATDRIVE_CRYPT",  "")
XSRF_TOKEN  = os.environ.get("XSRF_TOKEN",     "")
LARAVEL_SES = os.environ.get("Laravel_Session", "")


# ─────────────────────────────────────────────
# PROXY-AWARE HELPERS
# ─────────────────────────────────────────────

def _cloudscraper_client():
    """cloudscraper with proxy attached."""
    client = cloudscraper.create_scraper(allow_brotli=False)
    proxy = proxy_manager.get_proxy()
    if proxy:
        client.proxies.update(proxy)
    return client

def _session() -> requests.Session:
    """requests.Session with proxy attached."""
    return proxy_manager.get_requests_session()

def _get(url: str, **kwargs) -> requests.Response:
    """Proxy-aware GET."""
    proxies = proxy_manager.get_proxy()
    return requests.get(url, proxies=proxies or {}, timeout=20, **kwargs)

def _get_gdrive_id(link: str) -> str:
    if "folders" in link or "file" in link:
        res = re.search(
            r"https://drive\.google\.com/(?:drive.*?/folders/|file.*?/d/)([-\w]+)", link
        )
        return res.group(1) if res else ""
    parsed = urlparse(link)
    return parse_qs(parsed.query).get("id", [""])[0]

def _get_index_link(gdrive_link: str) -> str:
    gid = _get_gdrive_id(gdrive_link)
    return f"https://indexlink.mrprincebotz.workers.dev/direct.aspx?id={gid}"

async def _transcript(url: str, domain: str, referer: str, sleep_time: float) -> str:
    """Generic shortener bypass — POST to /links/go after sleep. Uses proxy."""
    code   = url.rstrip("/").split("/")[-1]
    client = _cloudscraper_client()
    resp   = client.get(f"{domain}/{code}", headers={"referer": referer}, allow_redirects=False)
    soup   = BeautifulSoup(resp.content, "html.parser")
    data   = {inp.get("name"): inp.get("value") for inp in soup.find_all("input")}
    await asyncio.sleep(sleep_time)
    resp   = client.post(f"{domain}/links/go", data=data,
                         headers={"x-requested-with": "XMLHttpRequest"})
    try:
        return resp.json()["url"]
    except Exception:
        return "Something went wrong :("


# ─────────────────────────────────────────────
# BYPASS FUNCTIONS  (all proxy-aware)
# ─────────────────────────────────────────────

def _gofile(url: str) -> str:
    sess = _session()
    resp = sess.get("https://api.gofile.io/createAccount")
    if resp.status_code != 200:
        return "ERROR: GoFile server response failed"
    data = resp.json()
    if data.get("status") != "ok" or not data.get("data", {}).get("token"):
        return "ERROR: Failed to create GoFile account"
    token = data["data"]["token"]

    def get_files(content_id, path):
        params = {"contentId": content_id, "token": token, "websiteToken": "7fd94ds12fds4"}
        r = sess.get("https://api.gofile.io/getContent", params=params)
        if r.status_code != 200:
            return {}
        jdata = r.json()
        if jdata.get("status") != "ok":
            return {}
        links = {}
        for c in jdata["data"]["contents"].values():
            if c["type"] == "folder":
                links.update(get_files(c["id"], path + "/" + c["name"]))
            elif c["type"] == "file":
                links[c["link"]] = path
        return links

    files = get_files(url.rsplit("/", 1)[-1], "")
    return list(files.keys())[0] if files else "ERROR: No files found"


def _drivefire(url: str) -> str:
    client = _session()
    client.cookies.update({"crypt": DCRYPT})
    client.get(url)
    parsed  = urlparse(url)
    req_url = f"{parsed.scheme}://{parsed.netloc}/ajax.php?ajax=download"
    try:
        file_path  = client.post(req_url, headers={"x-requested-with": "XMLHttpRequest"},
                                 data={"id": url.split("/")[-1]}).json()["file"]
        decoded_id = file_path.rsplit("/", 1)[-1]
        return f"https://drive.google.com/file/d/{decoded_id}"
    except Exception:
        return "Error"


def _kolop(url: str) -> str:
    client = _session()
    client.cookies.update({"crypt": KCRYPT})
    client.get(url)
    parsed  = urlparse(url)
    req_url = f"{parsed.scheme}://{parsed.netloc}/ajax.php?ajax=download"
    try:
        res   = client.post(req_url, headers={"x-requested-with": "XMLHttpRequest"},
                            data={"id": url.split("/")[-1]}).json()["file"]
        gd_id = re.findall(r"gd=(.*)", res, re.DOTALL)[0]
        return f"https://drive.google.com/open?id={gd_id}"
    except Exception:
        return "Error"


def _drivescript(url: str, crypt: str, dtype: str) -> str:
    sess   = _session()
    resp   = sess.get(url)
    title  = re.findall(r">(.*?)</h4>", resp.text)
    title  = title[0] if title else "Unknown"
    size   = re.findall(r">(.*?)</td>", resp.text)
    size   = size[1] if len(size) > 1 else "Unknown"
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    dlink  = ""

    if dtype != "DriveFire":
        try:
            js = sess.post(f"{base}/ajax.php?ajax=direct-download",
                           data={"id": url.split("/")[-1]},
                           headers={"x-requested-with": "XMLHttpRequest"}).json()
            if str(js.get("code")) == "200":
                dlink = f"{base}{js['file']}"
        except Exception as e:
            logger.error(e)

    if not dlink and crypt:
        sess.get(url, cookies={"crypt": crypt})
        try:
            js = sess.post(f"{base}/ajax.php?ajax=download",
                           data={"id": url.split("/")[-1]},
                           headers={"x-requested-with": "XMLHttpRequest"}).json()
            if str(js.get("code")) == "200":
                dlink = f"{base}{js['file']}"
        except Exception as e:
            return str(e)

    if dlink:
        res  = sess.get(dlink)
        soup = BeautifulSoup(res.text, "html.parser")
        gd   = soup.select('a[class="btn btn-primary btn-user"]')
        txt  = f"┎ <b>Name:</b> <code>{title}</code>\n┠ <b>Size:</b> <code>{size}</code>\n┃\n┠ <b>{dtype} Link:</b> {url}"
        if gd:
            d_link = gd[0]["href"]
            if dtype == "HubDrive" and len(gd) > 1:
                txt += f'\n┠ <b>Instant Link:</b> <a href="{gd[1]["href"]}">Click Here</a>'
            txt += f"\n┠ <b>Index Link:</b> {_get_index_link(d_link)}"
            txt += f"\n┖ <b>Drive Link:</b> {d_link}"
        return txt
    elif not crypt:
        return f"{dtype} Crypt not provided and direct link generation failed"
    return "Link generation failed"


def _mediafire(url: str) -> str:
    res = _get(url, stream=True)
    for line in res.text.splitlines():
        m = re.search(r'href="((https?)://download[^"]+)', line)
        if m:
            return m.group(1)
    return "Error: Download link not found"


def _dropbox(url: str) -> str:
    return (url.replace("www.", "")
               .replace("dropbox.com", "dl.dropboxusercontent.com")
               .replace("?dl=0", ""))


def _shareus(url: str) -> str:
    DOMAIN  = "https://us-central1-my-apps-server.cloudfunctions.net"
    headers = {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    sess    = _session()
    sess.headers.update(headers)
    code    = url.split("/")[-1]
    params  = {"shortid": code, "initial": "true", "referrer": "https://shareus.io/"}
    sess.get(f"{DOMAIN}/v", params=params)
    for i in range(1, 4):
        sess.post(f"{DOMAIN}/v", json={"current_page": i})
    return sess.get(f"{DOMAIN}/get_link").json()["link_info"]["destination"]


def _filecrypt(url: str) -> str:
    client  = _cloudscraper_client()
    headers = {
        "authority": "filecrypt.co", "content-type": "application/x-www-form-urlencoded",
        "referer": url, "origin": "https://filecrypt.co",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/105.0.0.0 Safari/537.36"
    }
    resp    = client.get(url, headers=headers)
    soup    = BeautifulSoup(resp.content, "html.parser")
    dlclink = None
    for btn in soup.find_all("button"):
        onclick = btn.get("onclick", "")
        if "DownloadDLC" in onclick:
            dlc_id  = onclick.split("DownloadDLC('")[1].split("'")[0]
            dlclink = f"https://filecrypt.co/DLC/{dlc_id}.html"
            break
    if not dlclink:
        return "Error: DLC link not found"
    resp = client.get(dlclink, headers=headers)
    links_resp = client.post(
        "http://dcrypt.it/decrypt/paste",
        headers={"X-Requested-With": "XMLHttpRequest", "Origin": "http://dcrypt.it",
                 "Referer": "http://dcrypt.it/"},
        data={"content": resp.text}
    ).json()
    return "\n".join(links_resp.get("success", {}).get("links", []))


def _adfly(url: str) -> str:
    def _decrypt(code):
        a, b = "", ""
        for i, c in enumerate(code):
            if i % 2 == 0: a += c
            else: b = c + b
        key = list(a + b)
        i = 0
        while i < len(key):
            if key[i].isdigit():
                for j in range(i + 1, len(key)):
                    if key[j].isdigit():
                        u = int(key[i]) ^ int(key[j])
                        if u < 10: key[i] = str(u)
                        i = j
                        break
            i += 1
        return base64.b64decode("".join(key))[16:-16].decode("utf-8")

    client = _cloudscraper_client()
    res    = client.get(url).text
    try:
        ysmm = re.findall(r"ysmm\s+=\s+['\"](.+?)['\"]", res)[0]
    except IndexError:
        return "Error: ysmm token not found"
    result = _decrypt(ysmm)
    if re.search(r"go\.php\?u=", result):
        return base64.b64decode(re.sub(r".*?u=", "", result)).decode()
    elif "&dest=" in result:
        return unquote(re.sub(r".*?dest=", "", result))
    return result


def _droplink(url: str) -> str:
    client = _cloudscraper_client()
    res    = client.get(url, timeout=5)
    ref    = re.findall(r"action\s*=\s*['\"](.+?)['\"]", res.text)[0]
    res    = client.get(url, headers={"referer": ref})
    soup   = BeautifulSoup(res.content, "html.parser")
    data   = {inp.get("name"): inp.get("value") for inp in soup.find_all("input")}
    parsed = urlparse(url)
    time.sleep(3.1)
    res = client.post(
        f"{parsed.scheme}://{parsed.netloc}/links/go", data=data,
        headers={"content-type": "application/x-www-form-urlencoded",
                 "x-requested-with": "XMLHttpRequest"}
    ).json()
    return res["url"] if res.get("status") == "success" else "Something went wrong"


def _linkvertise(url: str) -> str:
    resp = _get("https://bypass.pm/bypass2", params={"url": url}).json()
    return resp.get("destination") if resp.get("success") else resp.get("msg", "Failed")


def _ouo(url: str) -> str:
    def _recaptcha_v3():
        ANCHOR = "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6Lcr1ncUAAAAAH3cghg6cOTPGARa8adOf-y9zv2x&co=aHR0cHM6Ly9vdW8ucHJlc3M6NDQz&hl=en&v=pCoGBhjs9s8EhFOHJFe8cqis&size=invisible&cb=ahgyd1gkfkhe"
        sess   = _session()
        sess.headers["content-type"] = "application/x-www-form-urlencoded"
        kind, params = re.findall(r"([api2|enterprise]+)/anchor\?(.*)", ANCHOR)[0]
        base   = f"https://www.google.com/recaptcha/{kind}/"
        res    = sess.get(base + "anchor", params=params)
        token  = re.findall(r'"recaptcha-token" value="(.*?)"', res.text)[0]
        pdict  = dict(p.split("=") for p in params.split("&"))
        res    = sess.post(base + "reload", params=f'k={pdict["k"]}',
                           data=f"v={pdict['v']}&reason=q&c={token}&k={pdict['k']}&co={pdict['co']}")
        return re.findall(r'"rresp","(.*?)"', res.text)[0]

    url    = url.replace("ouo.press", "ouo.io")
    p      = urlparse(url)
    uid    = url.split("/")[-1]
    proxy  = proxy_manager.get_proxy_url()
    client = CurlSession(headers={
        "authority": "ouo.io",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "referer": "http://www.google.com/ig/adde?moduleurl=",
        "upgrade-insecure-requests": "1"
    }, proxies={"http": proxy, "https": proxy} if proxy else {})

    res      = client.get(url, impersonate="chrome110")
    next_url = f"{p.scheme}://{p.hostname}/go/{uid}"

    for _ in range(2):
        if res.headers.get("Location"):
            break
        soup   = BeautifulSoup(res.content, "lxml")
        inputs = soup.form.findAll("input", {"name": re.compile(r"token$")})
        data   = {inp.get("name"): inp.get("value") for inp in inputs}
        data["x-token"] = _recaptcha_v3()
        res = client.post(next_url, data=data,
                          headers={"content-type": "application/x-www-form-urlencoded"},
                          allow_redirects=False, impersonate="chrome110")
        next_url = f"{p.scheme}://{p.hostname}/xreallcygo/{uid}"

    return res.headers.get("Location", "Error: Location header not found")


def _sharer_pw(url: str) -> str:
    client = _cloudscraper_client()
    client.cookies.update({"XSRF-TOKEN": XSRF_TOKEN, "laravel_session": LARAVEL_SES})
    res   = client.get(url)
    token = re.findall(r"_token\s=\s'(.*?)'", res.text, re.DOTALL)[0]
    try:
        result = client.post(url + "/dl",
                             headers={"content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                                      "x-requested-with": "XMLHttpRequest"},
                             data={"_token": token, "nl": 1}).json()
        return result.get("url", "Error: URL not in response")
    except Exception as e:
        return f"Error: {e}"


def _gdtot(url: str) -> str:
    cget = _cloudscraper_client()
    try:
        url   = cget.get(url).url
        p_url = urlparse(url)
        res   = cget.post(f"{p_url.scheme}://{p_url.hostname}/ddl",
                          data={"dl": url.split("/")[-1]})
    except Exception as e:
        return f"{e.__class__.__name__}: {e}"

    drive_link = re.findall(r"myDl\('(.*?)'\)", res.text)
    if drive_link and "drive.google.com" in drive_link[0]:
        d_link = drive_link[0]
    elif GDTOT_CRYPT:
        cget.get(url, cookies={"crypt": GDTOT_CRYPT})
        js_script = cget.post(f"{p_url.scheme}://{p_url.hostname}/dld",
                               data={"dwnld": url.split("/")[-1]})
        g_id = re.findall(r"gd=(.*?)&", js_script.text)
        if not g_id:
            return "Try in your browser — file not found or limit exceeded"
        try:
            decoded_id = base64.b64decode(g_id[0]).decode("utf-8")
        except Exception:
            return "Try in your browser — mostly file not found or user limit exceeded"
        d_link = f"https://drive.google.com/open?id={decoded_id}"
    else:
        return "Drive link not found. GDTOT_CRYPT not provided."

    soup       = BeautifulSoup(cget.get(url).content, "html.parser")
    meta       = soup.select('meta[property^="og:description"]')
    parse_data = (meta[0]["content"]).replace("Download ", "").rsplit("-", maxsplit=1) if meta else ["Unknown", "Unknown"]
    return (
        f"┎ <b>Name:</b> <i>{parse_data[0]}</i>\n"
        f"┠ <b>Size:</b> <i>{parse_data[-1]}</i>\n┃\n"
        f"┠ <b>GDToT Link:</b> {url}\n"
        f"┠ <b>Index Link:</b> {_get_index_link(d_link)}\n"
        f"┖ <b>Drive Link:</b> {d_link}"
    )


def _mdisk(url: str) -> str:
    cid = url.split("/")[-1]
    res = _get(f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={cid}",
               headers={"Referer": "https://mdisk.me/",
                        "User-Agent": "Mozilla/5.0 Chrome/93.0.4577.82 Safari/537.36"}).json()
    return f"{res.get('download', '')}\n\n{res.get('source', '')}"


def _bitly_tinyurl(url: str) -> str:
    try:
        return _get(url).url
    except Exception:
        return "Something went wrong"


def _thinfi(url: str) -> str:
    try:
        resp = _get(url)
        return BeautifulSoup(resp.content, "html.parser").p.a.get("href", "Not found")
    except Exception:
        return "Something went wrong"


def _try2link(url: str) -> str:
    client = _cloudscraper_client()
    url    = url.rstrip("/")
    params = (("d", int(time.time()) + 240),)
    r      = client.get(url, params=params, headers={"Referer": "https://newforex.online/"})
    soup   = BeautifulSoup(r.text, "html.parser")
    inputs = soup.find(id="go-link")
    if not inputs:
        return "Error: go-link not found"
    data = {inp.get("name"): inp.get("value") for inp in inputs.find_all("input")}
    time.sleep(7)
    res = client.post("https://try2link.com/links/go", data=data,
                      headers={"Host": "try2link.com", "X-Requested-With": "XMLHttpRequest",
                               "Origin": "https://try2link.com", "Referer": url})
    return res.json().get("url", "Error: URL not found")


def _sh_st(url: str) -> str:
    client = _session()
    client.headers["referer"] = url
    p   = urlparse(url)
    res = client.get(url)
    try:
        sess_id = re.findall(r"sessionId\s*:\s*['\"](.+?)['\"]", res.text)[0]
    except IndexError:
        return "Error: sessionId not found"
    time.sleep(5)
    res = client.get(f"{p.scheme}://{p.netloc}/shortest-url/end-adsession",
                     params={"adSessionId": sess_id, "callback": "_"})
    return re.findall(r'"(.*?)"', res.text)[1].replace("\\/", "/")


async def _toonworld4all(url: str) -> str:
    client = _cloudscraper_client()
    if "/redirect/main.php?url=" in url:
        final = _get(url).url
        return f"┎ <b>Source:</b> {url}\n┃\n┖ <b>Bypass:</b> {final}"

    res  = client.get(url)
    soup = BeautifulSoup(res.content, "html.parser")

    if "/episode/" not in url:
        episodes = soup.select('a[href*="/episode/"]')
        headings = soup.select('div[class*="mks_accordion_heading"]')
        stitle   = re.search(r'"name":"(.+?)"', res.text)
        title    = stitle.group(1).split('"')[0] if stitle else "Unknown"
        prsd     = f"<b><i>{title}</i></b>"
        for n, (t, l) in enumerate(zip(headings, episodes), start=1):
            heading_text = t.strong.string if t.strong else "Episode"
            prsd += f"\n\n{n}. <i><b>{heading_text}</b></i>\n┖ <b>Link:</b> {l['href']}"
        return prsd

    links  = soup.select('a[href*="/redirect/main.php?url="]')
    titles = soup.select("h5")
    prsd   = f"<b><i>{titles[0].string}</i></b>" if titles else "<b>Links</b>"
    if titles:
        titles.pop(0)

    slicer = max(1, len(links) // len(titles)) if titles else 1
    tasks  = []
    for sl in links:
        nsl      = ""
        attempts = 0
        while not any(x in nsl for x in ["rocklinks", "link1s"]) and attempts < 5:
            try:
                nsl = _get(sl["href"], allow_redirects=False).headers.get("location", "")
            except Exception:
                break
            attempts += 1
        if "rocklinks" in nsl:
            tasks.append(asyncio.create_task(
                _transcript(nsl, "https://insurance.techymedies.com/", "https://highkeyfinance.com/", 5)
            ))
        elif "link1s" in nsl:
            tasks.append(asyncio.create_task(
                _transcript(nsl, "https://link1s.com/", "https://anhdep24.com/", 8)
            ))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    grouped = [results[i:i + slicer] for i in range(0, len(results), slicer)]

    for no, tl in enumerate(titles):
        prsd += f"\n\n<b>{tl.string}</b>\n┃\n┖ <b>Links:</b> "
        group = grouped[no] if no < len(grouped) else []
        parts = []
        for tlink, sl in zip(links, group):
            text = str(sl) if isinstance(sl, Exception) else f"<a href='{sl}'>{tlink.string}</a>"
            parts.append(text)
        prsd += ", ".join(parts)
    return prsd


async def _toonhub(url: str) -> str:
    client = _cloudscraper_client()
    if "redirect/?url" in url:
        location = client.get(url, allow_redirects=False).headers.get("Location", "")
        return await _shortners(location)

    res  = client.get(url)
    soup = BeautifulSoup(res.content, "html.parser")

    if "/episode/" not in url:
        title = soup.find("title")
        l = f"{title.text}\n" if title else ""
        for body, toggle in zip(
            soup.find_all("div", {"class": "three_fourth tie-columns last"}),
            soup.find_all("div", {"class": "toggle"})
        ):
            l += f'<a href="{toggle.a.get("href")}">{toggle.h3.text.strip()}\n</a>Context: {body.text}\n'
        return l

    links  = soup.select('a[href*="/redirect/?url="]')
    titles = soup.select("h5")
    prsd   = f"<b><i>{titles[0].string}</i></b>" if titles else "<b>Links</b>"
    if titles:
        titles.pop(0)

    slicer = max(1, len(links) // len(titles)) if titles else 1
    tasks  = []
    for sl in links:
        nsl = client.get(f"https://toonshub.link/{sl['href']}",
                         allow_redirects=False).headers.get("location", "")
        tasks.append(asyncio.create_task(_shortners(nsl)))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    grouped = [results[i:i + slicer] for i in range(0, len(results), slicer)]

    for no, tl in enumerate(titles):
        prsd += f"\n\n<b>{tl.string}</b>\n┃\n┖ <b>Links:</b> "
        group = grouped[no] if no < len(grouped) else []
        parts = []
        for tlink, sl in zip(links, group):
            text = str(sl) if isinstance(sl, Exception) else f"<a href='{sl}'>{tlink.string}</a>"
            parts.append(text)
        prsd += ", ".join(parts)
    return prsd


async def _atishmkv(url: str) -> str:
    client = _cloudscraper_client()
    res    = client.get(url)
    soup   = BeautifulSoup(res.content, "html.parser")
    title  = soup.find("title")
    l      = f"Title: {title.text}\n" if title else ""
    for a in soup.find_all("a", class_="button button-shadow"):
        l += f'➥<a href="{a.get("href")}">{a.get_text().strip()}</a> |\n'
    return l


async def _telegraph_scraper(url: str) -> str:
    res  = _get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    l    = "Scraped Links:\n"
    for strong, code in zip(soup.find_all("strong"), soup.find_all("code")):
        if strong.a:
            l += f'➥<a href="{strong.a.get("href")}">{code.get_text().strip()}</a> |\n'
    return l


# ─────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────

async def _shortners(url: str) -> str:
    u = url.lower()

    if "katdrive." in u:
        return _drivescript(url, KATCRYPT, "KatDrive") if KATCRYPT else "⚠️ KATDRIVE_CRYPT not set"
    if "kolop." in u:
        return _kolop(url) if KCRYPT else "⚠️ KOLOP_CRYPT not set"
    if "hubdrive." in u:
        return _drivescript(url, HCRYPT, "HubDrive") if HCRYPT else "⚠️ HUBDRIVE_CRYPT not set"
    if "drivefire." in u:
        return _drivefire(url) if DCRYPT else "⚠️ DRIVEFIRE_CRYPT not set"
    if "filecrypt.co" in u or "filecrypt.cc" in u:
        return _filecrypt(url)
    if "shareus." in u or "shrs.link" in u:
        return _shareus(url)
    if "gofile.io" in u:
        return _gofile(url)
    if "mediafire.com" in u:
        return _mediafire(url)
    if "dropbox.com" in u:
        return _dropbox(url)
    if "mdisk.me" in u:
        return _mdisk(url)
    if "gdtot" in u:
        return _gdtot(url)
    if "drive.google.com" in u:
        return f"🔗 Index Link: {_get_index_link(url)}"
    if "shorte.st" in u:
        return _sh_st(url)
    if "sharer.pw" in u:
        if not XSRF_TOKEN or not LARAVEL_SES:
            return "⚠️ XSRF_TOKEN / Laravel_Session not set"
        return _sharer_pw(url)
    if "adf.ly" in u:
        return _adfly(url)
    if "droplink.co" in u:
        return _droplink(url)
    if "linkvertise.com" in u:
        return _linkvertise(url)
    if "ouo.press" in u or "ouo.io" in u:
        return _ouo(url)
    if "try2link.com" in u:
        return _try2link(url)
    if "bit.ly" in u or "tinyurl.com" in u:
        return _bitly_tinyurl(url)
    if "thinfi.com" in u:
        return _thinfi(url)

    transcript_map = [
        ("shrinkforearn",  "https://shrinkforearn.in/",          "https://wp.uploadfiles.in/",          10),
        ("gplinks",        "https://gplinks.co/",                "https://gplinks.co/",                  5),
        ("link1s.com",     "https://link1s.com/",                "https://anhdep24.com/",                8),
        ("rocklinks",      "https://insurance.techymedies.com/", "https://highkeyfinance.com/",          5),
        ("droplink",       "https://droplink.co/",               "https://droplink.co/",                 3),
        ("linkfly",        "https://go.linkfly.in",              "https://techyblogs.in/",               4),
        ("narzolinks",     "https://go.narzolinks.click/",       "https://hydtech.in/",                  5),
        ("adsfly",         "https://go.adsfly.in/",              "https://loans.quick91.com/",           5),
        ("link4earn",      "https://link4earn.com",              "https://studyis.xyz/",                 5),
        ("sklinks",        "https://sklinks.in",                 "https://sklinks.in/",                  4.5),
        ("dalink",         "https://get.tamilhit.tech/X/LOG-E/","https://www.tamilhit.tech/",           8),
        ("sxslink",        "https://getlink.sxslink.com/",       "https://cinemapettai.in/",             5),
        ("seturl.in",      "https://set.seturl.in/",             "https://earn.petrainer.in/",           5),
        ("kpslink.in",     "https://get.infotamizhan.xyz/",      "https://infotamizhan.xyz/",            5),
        ("v2.kpslink.in",  "https://v2download.kpslink.in/",     "https://infotamizhan.xyz/",            5),
        ("linksly",        "https://go.linksly.co",              "https://en.themezon.net/",             10),
        ("linkbnao",       "https://vip.linkbnao.com",           "https://ffworld.xyz/",                 2),
        ("vipurl",         "https://count.vipurl.in/",           "https://awuyro.com/",                  8),
        ("tglink",         "https://tglink.in/",                 "https://www.proappapk.com/",           5),
        ("mdiskpro",       "https://mdisk.pro",                  "https://www.meclipstudy.in",           8),
        ("omegalinks",     "https://tera-box.com",               "https://m.meclipstudy.in",             8),
        ("ezlinks",        "https://ez4short.com/",              "https://ez4mods.com/",                 5),
        ("shortingly",     "https://go.blogytube.com/",          "https://blogytube.com/",               1),
        ("gyanilinks",     "https://go.hipsonyc.com",            "https://earn.hostadviser.net",         5),
        ("flashlinks.in",  "https://flashlinks.in",              "https://flashlinks.online/",           13),
        ("moonlinks",      "https://go.moonlinks.in/",           "https://www.akcartoons.in/",           7),
        ("krownlinks",     "https://go.hostadviser.net/",        "https://blog.hostadviser.net/",        8),
        ("indshort",       "https://indianshortner.com",         "https://moddingzone.in",               5),
        ("indianshortner", "https://indianshortner.com/",        "https://moddingzone.in",               5),
        ("shrinke",        "https://en.shrinke.me/",             "https://themezon.net/",                15),
        ("earnl",          "https://v.earnl.xyz",                "https://link.modmakers.xyz",           5),
        ("v2links",        "https://vzu.us",                     "https://gadgetsreview27.com",          15),
        ("tnvalue",        "https://get.tnvalue.in/",            "https://finclub.in",                   8),
        ("urlspay.in",     "https://finance.smallinfo.in/",      "https://loans.techyinfo.in/",          5),
        ("linkpays.in",    "https://tech.smallinfo.in/Gadget/",  "https://loan.insuranceinfos.in/",      5),
    ]
    for keyword, domain, referer, sleep in transcript_map:
        if keyword in u:
            return await _transcript(url, domain, referer, sleep)

    if "toonworld4all.me/redirect/main.php" in u:
        nsl      = ""
        attempts = 0
        while not any(x in nsl for x in ["rocklinks", "link1s"]) and attempts < 5:
            nsl = _get(url, allow_redirects=False).headers.get("location", "")
            attempts += 1
        if "rocklinks" in nsl:
            return await _transcript(nsl, "https://insurance.techymedies.com/", "https://highkeyfinance.com/", 5)
        elif "link1s" in nsl:
            return await _transcript(nsl, "https://link1s.com/", "https://anhdep24.com/", 8)
        return "Error: Could not resolve redirect"

    if "toonworld4all" in u:
        return await _toonworld4all(url)
    if "toonshub" in u:
        return await _toonhub(url)
    if "atishmkv.wiki" in u:
        return await _atishmkv(url)
    if "graph.org" in u:
        return await _telegraph_scraper(url)

    return "Not in supported sites"


# ─────────────────────────────────────────────
# BYPASS CLASS
# ─────────────────────────────────────────────

@register_bypass
class UniversalBypass(BaseBypass):
    METHOD_NAME = "universal"
    PRIORITY    = 10
    TIMEOUT     = 60

    async def bypass(self, url: str) -> BypassResult:
        start = time.time()
        try:
            logger.info(f"[Universal] Attempting: {url} | {proxy_manager.status}")
            result = await _shortners(url)

            if result and result not in ("Not in supported sites", "Something went wrong :(") \
                    and not result.startswith("ERROR") and not result.startswith("Error") \
                    and not result.startswith("⚠️"):
                return BypassResult.success_result(
                    url=result,
                    method=self.METHOD_NAME,
                    execution_time=time.time() - start,
                    metadata={"technique": "universal_router",
                              "proxy_status": proxy_manager.status}
                )
            return BypassResult.failed_result(
                error_message=result or "No result returned",
                method=self.METHOD_NAME,
                execution_time=time.time() - start
            )
        except Exception as e:
            logger.error(f"[Universal] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=time.time() - start,
                status=BypassStatus.ERROR
            )
