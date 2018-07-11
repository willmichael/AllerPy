from apscheduler.schedulers.blocking import BlockingScheduler

from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import datetime
import re

from bs4 import BeautifulSoup as bs
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import smtplib
import email_creds

sched = BlockingScheduler()

@sched.scheduled_job('cron', day_of_week='mon-sun', hour=23)
def scheduled_job():
    print('This job is run every day at 12')
    loc = get_future_events()
    data = get_pollen_data(loc)
    send_email(data, loc)
# sched.start()


# Setup the Calendar API
def setup():
    SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))
    return service


def get_future_events():
    service = setup()
    now = datetime.datetime.utcnow() 
    next_day = now + datetime.timedelta(hours=24)

    now = now.isoformat() + 'Z'
    next_day = next_day.isoformat() + 'Z'

    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=next_day,
                                      maxResults=1, singleEvents=True,
                                      orderBy='startTime').execute()
    events = events_result.get('items', [])
    # (Location, What-doing)
    locations = []
    if not events:
        return '97229'
    # should be one event
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        locationStr = event['location']
        locZip = re.match(r'[\d]+', locationStr)
        locations.append((locZip, event['summary']))
        # print(start, event['summary'], locZip[0], event['location'])
    return locZip[0]



def get_pollen_data(location):
    # automatically parse charted[2] which should correspond to 'tmr'
    if not location:
        location = '97229'

    baseurl = "https://www.pollen.com/forecast/current/pollen/"
    url = baseurl + str(location)
    driver = webdriver.Chrome()
    driver.implicitly_wait(5)
    driver.get(url)

    soup = bs(driver.page_source, 'html.parser')
    charted = soup.find_all('div', class_='chart-col')
    tmr_level = charted[2].find('p', class_='forecast-level')
    if tmr_level:
        return tmr_level.get_text()
    else:
        return "Could Not Find"

def deliver_pollen_warning(warn_info):
    pass

def send_email(warn_info, locZip):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    userName = email_creds.email_login['email']
    password = email_creds.email_login['password']
    sendName = email_creds.send_to['email'] 


    server.login(userName, password)

    msg = 'pollen level ' + warn_info + ' for tomorrow at zip ' + locZip + ' consider taking your medicine'
    # print(msg)
    server.sendmail(userName, sendName, msg)
    server.quit()

