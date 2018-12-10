import json
import sys
import traceback
from ftplib import FTP
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.exceptions import MissingSchema
from vk_api import VkApi, ApiError, VkUpload
from vk_api.longpoll import VkLongPoll


def parse_remote_folder(url):
    out = {'/': []}
    try:
        request = requests.get(url)
    except MissingSchema:
        print('Wrong url!')
        exit()
    except requests.exceptions.ConnectionError:
        print('Can\'t connect to remote server!')
        exit()
    for tag in BeautifulSoup(request.text, features="html.parser").find_all('a'):
        if tag.text.endswith('.png'):
            out['/'].append(tag.text)
        elif tag.text.endswith('/'):
            out.update({tag.text[:-1]: parse_remote_folder(url + tag.text[:-1])['/']})
    return out


try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    if config['token']:
        session = VkApi(token=config['token'], api_version='5.89')
    else:
        session = VkApi(login=config['login'], password=config['password'], api_version='5.89')
        try:
            session.auth()
        except ApiError:
            print(traceback.format_exc())
            exit(0)
    api = session.get_api()

    base_stickers_url = sys.argv[1]
    stickers = []
    for s in parse_remote_folder(base_stickers_url):
        for i in parse_remote_folder(base_stickers_url)[s]:
            stickers.append(f'{s}.{i[:-4]}' if s != '/' else i[:-4])
    if len(stickers) == 0:
        print('No stickers initialized!')
        exit()
    print(f'Initialized {len(stickers)} stickers')
    lp = VkLongPoll(session)
    up = VkUpload(session)
    for event in lp.listen():
        if event.from_me and event.text.startswith('!') and event.text.endswith('!') and event.text[1:-1] in stickers:
            path = Path('stickers/' + event.text[1:-1] + '.png')
            if not path.exists():
                with open('stickers/' + event.text[1:-1] + '.png', 'wb') as f:
                    f.write(requests.get(base_stickers_url + event.text[1:-1].replace('.', '/') + '.png').content)

            sticker = up.graffiti('stickers/' + event.text[1:-1] + '.png', event.peer_id)[0]
            api.messages.delete(message_ids=event.message_id, delete_for_all=True)
            api.messages.send(peer_id=event.peer_id, attachment=f'doc{sticker["owner_id"]}_{sticker["id"]}')
except KeyboardInterrupt:
    print('Shutting down...')
