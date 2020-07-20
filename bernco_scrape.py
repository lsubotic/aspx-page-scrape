from multiprocessing.pool import ThreadPool
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from pprint import pprint
import requests
import csv
import os
import time
import re


url = r'https://wwp.bernco.gov/property_tax_search.aspx'  # source url
get_url = r'https://wwp.bernco.gov/property-tax-search-result/'  # url for the GET request

paginate_url = r'https://wwp.bernco.gov/property_tax_search_result.aspx'  # url for pagination


def get_source():
    """
    Creates a session, does a request to the first url, returns the page soup
    """
    try:
        user_agent = UserAgent().random
    except:
        user_agent = r'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
    headers = {
        'User-Agent': user_agent,
        'Sec-Fetch-Dest': 'document',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    global s
    s = requests.Session()
    s.headers.update(headers)
    r = s.get(url, timeout=7)
    print(f'Request to {url} --- {r.status_code}')
    soup = BeautifulSoup(r.text, 'lxml')
    return soup


def get_index(soup):
    """
    Returns a dict with all the indexes(name:value) extracted from the soup needed to load the next page
    """
    index_table = soup.select('td[style="white-space:nowrap;"] > input')  # select all table rows
    index_dict = {row.get('name'): row.get('value') for row in index_table}

    return index_dict


def get_viewstates(soup):
    """
    Takes in soup and gets all the viewstate data needed to load the next page (also gets __eventvalidation and __eventtarget)
    """
    str_soup = str(soup)
    data_dict = dict()

    event_val = soup.select_one("#__EVENTVALIDATION")  # __EVENTVALIDATION
    if event_val:  # if event validation is in html
        all_vs = soup.select("input[name*='__VIEWSTATE']")  # select all elements with viewstate in it
        data_dict = {vs.get('name'): vs.get('value') for vs in all_vs}  # get all viewstates from html
        data_dict.update({event_val.get('id'): event_val.get('value')})  # get __EVENTVALIDATION
    else:  # outside of html - regex use needed
        re_match = re.findall(r'(__VIEWSTATE?\w+)\|(.+?)\|', str_soup)
        next_button = soup.select_one('.rgWrap.rgArrPart2 > input').get('name')  # 'next' button update is needed every 10 pages
        if re_match:
            data_dict = {i[0]: i[1] for i in re_match}
            data_dict.update({'__EVENTTARGET': str(next_button)})
            data_dict.update({'ctl03$TemplateBody$ctl00$radScriptManager': 'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$placeHolder$ctl00$ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$placeHolder$ctl00$panelPanel|' + str(next_button)})
        else:
            'Did not find VIEWSTATE regex!'
        event_val = re.search(r'__EVENTVALIDATION\|(.+?)\|', str_soup)
        if event_val:
            data_dict.update({'__EVENTVALIDATION': event_val.group(1)})
        else:
            print('Did not find __EVENTVALIDATION regex')

    return data_dict


def do_search():
    """
    Performs a search by 'Number(only)' for the first PARCEL page and loads it
    """
    source_soup = get_source()  # get source soup

    data = {  # data on the search options and the values that are filled in
        # eventtarget is the 'search' button, later it WILL BE the 'next' button
        '__EVENTTARGET': 'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$ctl00$submit',
        'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$ctl00$number': '112',
        'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$ctl00$street': '',
        'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$ctl00$direction': 'All',
        'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$ctl00$displayOption': '1',
        'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$ctl00$year': '2019',
    }
    data.update(get_viewstates(source_soup))  # get viewstates and __EVENTVALIDATION
    s.headers.update({'Origin': 'https://wwp.bernco.gov',
                      'Sec-Fetch-Site': 'same-origin',
                      'Sec-Fetch-Mode': 'cors',
                      'Referer': 'https://wwp.bernco.gov/property_tax_search.aspx',
                      'X-MicrosoftAjax': 'Delta=true'})

    # get the first parcel list
    r = s.post(url, data=data)
    print(f'Request to {url} --- {r.status_code}')
    r = s.get(get_url)
    soup = BeautifulSoup(r.text, 'lxml')  # successfully got the parcel list page!

    return soup


def extract_parcels(soup):
    """
    Extract parcel data and write into csv file
    """
    table = soup.select('tfoot + tbody > tr')  # select all table rows
    print(f'{len(table)} parcels found')
    for row in table:
        parcel_id = row.select_one('a').text
        address = row.select_one('span').text

        csv_writer.writerow([parcel_id, address])

 
def paginate():
    """
    Goes through pages of parcel lists until end
    """
    soup = do_search()
    extract_parcels(soup)  # extract data from the 1st parcels page

    # Paginating
    params = (  # params are needed here now in order to paginate(i guess)
        ('requested_url', 'property-tax-search-result'),
    )
    s.headers.update({'Referer': 'https://wwp.bernco.gov/property-tax-search-result/'})

    next_button = soup.select_one('.rgWrap.rgArrPart2 > input').get('name')  # 'next' button
    paginate_data = {
        # eventtarget is the 'next' button now
        '__EVENTTARGET': str(next_button)
    }

    paginate_data.update(get_viewstates(soup))  # update data with viewstates
    paginate_data.update(get_index(soup))  # update data with indexes
    paginate_data.update({  # constant data
        'ctl03$TemplateBody$ctl00$radScriptManager': 'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$placeHolder$ctl00$ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$placeHolder$ctl00$panelPanel|' + str(next_button),
        'p_PageAlias': 'property-tax-search-result',
        'ctl03$TemplateBody$ctl00$PageLayout$ctl00$Placeholder3$ctl00$pageContent$ctl00$Placeholder5$ctl00$placeHolder$ctl00$resultList$ctl00$ctl03$ctl01$PageSizeComboBox': '50',
        'ctl03_TemplateBody_ctl00_PageLayout_ctl00_Placeholder3_ctl00_pageContent_ctl00_Placeholder5_ctl00_placeHolder_ctl00_resultList_ctl00_ctl03_ctl01_PageSizeComboBox_ClientState': '{"logEntries":[],"value":"50","text":"50","enabled":true}',
    })

    i = 0
    page_count = soup.select_one('.rgWrap strong + strong').text
    while i < int(page_count):
        print(f'{i} ---  request to {paginate_url}')
        r = s.post(paginate_url, params=params, data=paginate_data)
        time.sleep(r.elapsed.total_seconds())

        soup = BeautifulSoup(r.text, 'lxml')
        extract_parcels(soup)
        paginate_data.update(get_viewstates(soup))  # updates the data
        paginate_data.update(get_index(soup))

        i += 1


def csv_write():
    """
    Main function which creates an global writer object
    """
    write_path = r'bernco.csv'
    with open(write_path, 'w', newline='', encoding='utf-8') as f:
        global csv_writer
        csv_writer = csv.writer(f)
        csv_writer.writerow(['PARCEL ID', 'SITUS ADDRESS'])

        paginate()

    # Starting the .csv file after finished
    os.startfile(write_path) 


if __name__ == "__main__":
    csv_write()













