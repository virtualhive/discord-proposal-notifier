#!/usr/bin/python3

# run with crontab every 4 hours
# 0 */4 * * * python3 /<path-to>/proposal-notifier.py | tee /<path-to>/proposal-notifier.log

import requests
import os.path, sys
from datetime import datetime
from dateutil import parser


BOT_NAME="[VH] Proposal Bot"
PING="@here"
THUMBNAIL="https://raw.githubusercontent.com/cosmos/chain-registry/master/cosmoshub/images/atom.png"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."
REST_API_URL = "https://rest.cosmos.directory/cosmoshub"
CHAIN_NAME = "Cosmos"


def log(message: str):
    print(f'{datetime.now()} - {message}')

def read_cache(cache_file_path):
    cache = []
    if os.path.exists(cache_file_path):
        with open(cache_file_path) as c:
            for proposal_id in c:
                cache.append(proposal_id.strip())
    return cache

def write_cache(cache, cache_file_path):
    with open(cache_file_path, 'w') as c:
        for proposal_id in cache:
            c.write(f"{proposal_id}\n")

def send_discord_message(CHAIN_NAME: str, proposal_id: int, discord_hook_url: str, prop_title: str, prop_descr: str, timestamp: str, link: str):
    data = {
            "username": BOT_NAME,
            "content": PING
    }

    data["embeds"] = [
        {
            "author": {
                "name": f"📨 New {CHAIN_NAME} Proposal 📨\n\u200B"
            },
            "title": f"{prop_title}\n\u200B",
            "color": 35009,
            "fields": [{
                    "name": "Chain",
                    "value": f"`{CHAIN_NAME}`",
                    "inline": True
                }, {
                    "name": "ID",
                    "value": f"`{str(proposal_id)}`",
                    "inline": True
                }, {
                    "name": "Voting End Time",
                    "value": timestamp,
                    "inline": True
                }, {
                    "name": "Link",
                    "value": link
                }, {
                    "name": "Description",
                    "value": f"```{prop_descr}```"
                }
            ],
            "thumbnail": {
                "url": THUMBNAIL
            },
            "footer": {
                "text": "powered by Virtual Hive",
                "icon_url": "https://virtualhive.io/img/favicon-16x16.png"
            }
        }
    ]

    try:
        result = requests.post(discord_hook_url, json = data, timeout=5)
    except requests.exceptions.Timeout:
        log("Request timeout. Retrying...")
        return send_discord_message(CHAIN_NAME, proposal_id, discord_hook_url, prop_title, prop_descr, timestamp, link)

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if (result.status_code == 429):
            log("Discord is rate limiting. Retrying...")
            return send_discord_message(CHAIN_NAME, proposal_id, discord_hook_url, prop_title, prop_descr, timestamp, link)
        else:
            log(err)
            log(result.headers)
            return False
    else:
        log("Payload delivered successfully, code {}.".format(result.status_code))
        return True


def send_discord(proposal_array: list, CHAIN_NAME: str, url: str):
    sent_props = []
    for i in range(len(proposal_array)):
        prop_id = int(proposal_array[i]['proposal_id'])
        if proposal_array[i]['content'] is None:
            prop_title = "N/A"
        elif 'title' in proposal_array[i]['content']:
            prop_title = proposal_array[i]['content']['title']
        else:
            prop_title = "N/A"
        voting_end = proposal_array[i]['voting_end_time']
        voting_end_unix_timestamp = int(datetime.timestamp(parser.isoparse(voting_end)))
        prop_descr = proposal_array[i]['content']['description']
        if len(prop_descr) > 400:
            prop_descr = f"{prop_descr[:397]}..."
        if send_discord_message(CHAIN_NAME, prop_id, url, prop_title, prop_descr, f"<t:{voting_end_unix_timestamp}:R>", f"https://www.mintscan.io/{CHAIN_NAME}/proposals/{prop_id}"):
            sent_props.append(prop_id)
    return sent_props

def process_props(CHAIN_NAME: str, rest_proposal_url: str, discord_hook_url: str, cache: list):
    log(f"Processing {CHAIN_NAME} Proposals...")
    r = requests.get(rest_proposal_url)

    prop_info = r.json()['proposals']

    new_props = []

    for prop in prop_info:
        if prop['proposal_id'] not in cache:
            log(prop['proposal_id'])
            new_props.append(prop)

    if len(new_props) > 0:
        log("Trying to send to discord...")
        return send_discord(new_props, CHAIN_NAME, discord_hook_url)
    else:
        return [] # empty array of new cache items


cache_file_path = f"{os.path.dirname(os.path.abspath(sys.argv[0]))}/proposal_notifier_cache.txt"
rest_proposal_url = f"{REST_API_URL}/cosmos/gov/v1beta1/proposals?proposal_status=2"

log('--------START----------')
if os.path.exists(cache_file_path):
    cache = read_cache(cache_file_path)
else:
    cache = []
cache.extend(process_props(CHAIN_NAME, rest_proposal_url, DISCORD_WEBHOOK_URL, cache))
write_cache(cache, cache_file_path)
log('---------END-----------')
