import hashlib
import json
import logging
import os
import requests
import time
import urllib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

INTERVAL = 60  # Seconds
PUSH_API_KEY = os.env['PUSH_API_KEY']
PUSH_URL = os.env.get('PUSH_API_URL', 'https://api.simplepush.io/send')

DUMP_CHECK_API_URL = "https://submit.jotformeu.com/server.php"

last_notification_checksum = None

def dump_check_args():
    timestr = str(int(time.time()))
    payload = {
        'action': 'getAppointments',
        'formID': '201591865335358',
        'timezone': 'Europe/London (GMT+01:00)',
#        'ncTz': str(timestr),
        'firstAvailableDates': None
    }
    params = urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
    return params

def push(title, message):
    resp = requests.post(
        PUSH_URL,
        data={
            'key': PUSH_API_KEY,
            'title': title,
            'msg': message
         }
    )
    return resp.ok

def check_slots():
   cookies = {'theme': 'tile-black', 'guest': 'guest_b919c00da0366ef1' }
   r = requests.get(DUMP_CHECK_API_URL, params=dump_check_args(), cookies=cookies)
   return r.json()

def run():
    global last_notification_checksum
    logger.info('Checking slots...')
    result = check_slots()
    dates = result['content']['21']
    if not dates:
        logger.info('No slots found')
        return False

    bookable_dates = {
        bookable: dates[bookable]
        for bookable in dates.keys()
        if dates[bookable]
    }
    notification_checksum = hashlib.sha256(
         json.dumps(
             bookable_dates, sort_keys=True
         ).encode('utf-8')
    ).hexdigest()

    logger.info('Found slots on %s', bookable_dates)
    if notification_checksum == last_notification_checksum:
        logger.info('Already send a notification for this message, skipping.')
        return True

    message = ''
    for d in sorted(bookable_dates):
        message += "%(date)s: %(slots)s" % {
            'date': d,
            'slots': ', '.join(
                [t for t, available in  bookable_dates[d].items() if available]
            )
        }

    logger.info('Sending push notification')
    r = push('Found dump slots', message)
    if r:
        last_notification_checksum = notification_checksum
        logger.info('Sent notification')
        return True
    else:
        logger.error('Failed to send notification')
        return False

while True:
    run()
    logger.info('Sleeping for %d seconds', INTERVAL)
    time.sleep(INTERVAL)
