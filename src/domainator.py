import re
import socket
from urllib.parse import *

import bs4
import requests

from .crawler import Crawler
from .utils import *


class Domainator:

    def __init__(self):

        # Verify domain integrity
        arg = parse_arg()
        if '://' in arg:
            parsed = urlsplit(arg)
        else:
            self.scheme = 'http'
            parsed = urlsplit(self.scheme + '://' + arg)

        if not parsed.netloc and '.' not in parsed.path:
            pr('Invalid domain!', '!')
            exit()

        self.domain = parsed.netloc
        self.scheme = parsed.scheme if parsed.scheme else 'http'
        print()
        pr('Using domain: ' + fc + self.domain)

        self.known_subdomains = set()
        self.crawler = Crawler(self, parsed.path)

        # self.ip = IPv4Address(socket.gethostbyname(self.domain))
        # pr('Host resolved: ' + cl.c + str(self.ip))

    def pack_url(self, subdomain='www', path=''):
        return urlunsplit((self.scheme, subdomain + '.' + self.domain, path, '', ''))

    def banners_cloud_flare(self):
        pr('Retrieving headers', '#')
        domain = self.pack_url()
        res = REQ_S.get(domain)
        if res.status_code != 200:
            pr('Bad status code: %d' % res.status_code, '!')
            return

        pr('Headers:')
        for h in res.headers.items():
            x = f'{h[0]} => {h[1]}'
            pr(x, '#')

        pr('Checking for CloudFlare in headers', '#')
        if "cloudflare" not in res.text:
            pr(self.domain + " is not using Cloudflare!")
            return

        if not pause('Attempt to bypass?'):
            return
        pr("CloudFlare found, attempting to bypass..")

        # TODO TEST

        url = "http://www.crimeflare.biz/cgi-bin/cfsearch.cgi"
        res = REQ_S.get(url, data={'cfS': self.domain})
        reg = re.findall(r'\d+\.\d+\.\d+\.\d+', res.text)
        if reg:
            real_ip = reg[1]
        else:
            pr("CloudFlare wasn't bypassed, No real IP found", '!')
            return
        res = REQ_S.get(f"http://{real_ip}")
        if "cloudflare" not in res.text.lower():
            if real_ip:
                pr("#", "Cloudflare Bypassed!")
                pr("+", "Real IP ==> " + fb + real_ip)
            return real_ip
        else:
            pr("Cloudflare wasn't bypassed, Real IP blocked by CloudFlare", '!')

    def reverse_HT(self):
        url = "http://api.hackertarget.com/reverseiplookup/?q=" + self.domain
        res = REQ_S.get(url)
        if res.status_code != 200:
            pr('Bad status code: %d' % res.status_code, '!')
            return
        lst = res.text.strip().split("\n")

        fn = f'./{self.domain}-reverseHT'
        with open(fn, 'w') as f:
            for l in lst:
                if l:
                    f.write(l.strip() + '\n')
                    # pr(l, '#')
        print()
        pr(f'Dumped {len(lst)} entries to "{fn}"\n')

    def reverse_YGS(self):
        url = "https://domains.yougetsignal.com/domains.php"
        data = {
            'remoteAddress': self.domain,
            'key': ''
        }
        res = REQ_S.get(url, params=data)
        if res.status_code != 200:
            pr('Bad status code: %d' % res.status_code, '!')
            # return

        grab = res.json()
        if 'fail' in grab['status'].lower():
            pr("Message:", '#')
            print(grab['message'])
            return

        pr("Results from: " + grab['lastScrape'], '#')
        pr("IP: " + grab['remoteIpAddress'], '#')
        pr("Domain: " + grab['remoteAddress'], '#')
        pr(f"Total Domains: {grab['domainCount']}\n", '#')
        for x, _ in grab['domainArray']:
            pr(x, '#')

    def find_subdomains(self):
        print("{}{:<62}| {:<50}".format(fc, "URL", "STATUS"))
        with open('./src/subdomains') as f:
            subdomains = f.readlines()
        try:
            for sub in subdomains:
                url = self.pack_url(subdomain=sub.strip())
                try:
                    res = REQ_S.get(url)
                    if res.status_code != 404:
                        if res.status_code == 200:
                            self.known_subdomains.add(f'{sub.strip()}.{self.domain}')
                        print("{}{:<62}| {:<50}".format(fg, url, res.status_code))
                except:
                    print("{}{:<62}| {:<50}".format(fr, url, 'ERROR'))
        except KeyboardInterrupt:
            pass

    def speed_check(self):
        import time

        start = time.time()
        ip = socket.gethostbyname(self.domain)
        dns_tm = time.time() - start
        _dns = "{:<10}:{:<20} seconds".format("DNS", dns_tm)
        pr(_dns, '#')

        start = time.time()
        _data = REQ_S.get(self.pack_url())
        load_tm = time.time() - start
        _load = "{:<10}:{:<20} seconds".format("Load", load_tm)
        _wo = "{:<10}:{:<20} seconds".format("W/O DNS", load_tm - dns_tm)

        pr(_load, '#')
        pr(_wo, '#')

    def whois(self):
        url = 'https://www.whois.com/whois/' + self.domain
        try:
            res = REQ_S.get(url)
            if res.status_code != 200:
                pr('Bad status code: %d' % res.status_code, '!')
                return
            bs = bs4.BeautifulSoup(res.content, 'html.parser')
            result = bs.find_all('pre', {'class': 'df-raw'})[0].text
            print(f"\n{fc + result + fx}")
        except requests.exceptions.RequestException:
            from traceback import print_exc
            print_exc()