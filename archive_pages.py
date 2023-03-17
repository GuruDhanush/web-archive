from xml.etree import ElementTree
import os
import logging
import time
import requests

S3_ACCESS_KEY = os.environ.get('s3_access_key')
S3_SECRET_KEY = os.environ.get('s3_secret_key')
ARCHIVE_SAVE_URL = 'https://web.archive.org/save'

SITE_MAP_PREFIX = '{http://www.sitemaps.org/schemas/sitemap/0.9}'

site_map_urls = [
    'https://amarahospital.com/page-sitemap.xml'
]

# SPN2 docs: https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA/edit#heading=h.1gmodju1d6p0

def get_site_xml(site_url: str):
    logging.info(f'Get site map from {site_url}')
    resp = requests.get(site_url)
    resp.raise_for_status()

    logging.info(f'Parsing XML for {site_url}')
    root = ElementTree.fromstring(resp.content)

    return root

def get_urls_sitemap(tree: ElementTree):
    urls = []
    all_url_elements = tree.findall(f'./{SITE_MAP_PREFIX}url/{SITE_MAP_PREFIX}loc')

    logging.info(f'Extracting all urls from sitemap')

    for url_elem in all_url_elements:
        current_url = url_elem.text
        if current_url:
            urls.append(current_url)
    
    return urls

def archive_page(url: str):
    headers = {
        'Accept': 'application/json',
        'Authorization': f'LOW {S3_ACCESS_KEY}:{S3_SECRET_KEY}' 
    }
    body = {
        'url': url,
        'delay_wb_availability': 1,
        'skip_first_archive': 1,
        'if_not_archived_within': '15h'
    }
    try:
        resp = requests.post(ARCHIVE_SAVE_URL, headers=headers, data=body)

        if resp.status_code != 200:
            data = resp.text
            logging.warning(f'Unable to archive page {url} due to {data}')
        else:
            data = resp.json()
            logging.info(f'Archived page under {data.get("url")} via {data.get("job_id")}')
            if data.get('message'):
                logging.warning(f'Message: {data.get("message")}')
    except Exception as ex:
        logging.warning(str(ex))

def main():
    # Get all site URLS from sitemap
    all_urls = []
    for site in site_map_urls:
        site_xml = get_site_xml(site)
        all_urls = all_urls + get_urls_sitemap(site_xml)
    
    for url in all_urls:
        # sleep for 10 seconds before making API call as we have limit of 12 pages/minute
        time.sleep(10)
        archive_page(url)

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    main()
    