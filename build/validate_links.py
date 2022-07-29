#!/usr/bin/env python3

import httplib2
import re
import socket
import sys


def parse_links(filename):
    """Returns a list of URLs from text file"""
    with open(filename, mode='r', encoding='utf-8') as fp:
        readme = fp.read()
        index_section = readme.find('## Index')
        content = readme[index_section:]

    raw_links = re.findall(
        '((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’]))',
        content)

    return [str(raw_link[0]).rstrip('/') for raw_link in raw_links]

def dup_links(links):
    """Check for duplicated links"""
    print('Checking for duplicated links...')
    hasError = False
    seen = {}
    dupes = []

    for link in links:
        if link not in seen:
            seen[link] = 1
        elif seen[link] == 1:
            dupes.append(link)

    if not dupes:
        print("No duplicate links")
    else:
        print(f"Found duplicate links: {dupes}")  
        hasError = True
    return hasError

def validate_links(links):
    """Checks each entry in JSON file for live link"""
    print(f'Validating {len(links)} links...')
    hasError = False
    for link in links:
        h = httplib2.Http(disable_ssl_certificate_validation=True, timeout=25)
        try:
            # fetching host name, removing leading www
            host = link.split('//', 1)[1].split('/', 1)[0]
            if host[:3] == 'www':
                host = host[4:]

            resp = h.request(
                f"{link}/",
                headers={
                    # Faking user agent as some hosting services block not-whitelisted UA
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1467.0 Safari/537.36',
                    # setting host because Cloudflare returns 403 asking for captcha if host is missing
                    'host': host,
                },
            )

            code = int(resp[0]['status'])
            # Checking status code errors
            if (code >= 400):
                hasError = True
                print(f"ERR:CLT:{code} : {link}")
        except TimeoutError:
            hasError = True
            print(f"ERR:TMO: {link}")
        except socket.error as socketerror:
            hasError = True
            print(f"ERR:SOC: {socketerror} : {link}")
        except Exception as e:
            hasError = True
            # Ignore some exceptions which are not actually errors.
            # The list below should be extended with other exceptions in the future if needed
            if (
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:852)"
                in str(e)
            ):
                print(f"ERR:SSL: {e} : {link}")
            elif (
                "Content purported to be compressed with gzip but failed to decompress."
                in str(e)
            ):
                print(f"ERR:GZP: {e} : {link}")
            elif "Unable to find the server at" in str(e):
                print(f"ERR:SRV: {e} : {link}")
            else:
                print(f"ERR:UKN: {e} : {link}")
    return hasError

if __name__ == "__main__":
    num_args = len(sys.argv)
    if num_args < 2:
        print("No .md file passed")
        sys.exit(1)
    links = parse_links(sys.argv[1])
    if hasError := dup_links(links) or validate_links(links):
        sys.exit(1)
