import json
import os
import pickle
import traceback

import requests
from vk_api import VkApi, ApiError, VkUpload
from vk_api.execute import VkFunction
from vk_api.longpoll import VkLongPoll, VkEventType


def captcha_handler(c):
    with open('captcha.jpg', 'wb') as file:
        file.write(requests.get(c.url).content)
    reply('Enter captcha from "captcha.jpg"')
    code = input('Enter captcha from "captcha.jpg"\n')
    return c.try_again(code)


reply = lambda m='', a='': api.messages.send(peer_id=event.peer_id, message=m, attachment=a)

vk_send_sticker = VkFunction(args=('message_ids', 'peer_id', 'attachment'),
                             code='''
                             API.messages.delete({"message_ids": %(message_ids)s, 
                                                  "delete_for_all": true});
                             API.messages.send({"peer_id": %(peer_id)s, "attachment": %(attachment)s});                             
                             ''')


def open_cache():
    global cache
    try:
        cache = pickle.load(open('cache.pkl', 'rb'))
    except FileNotFoundError:
        pickle.dump({}, open('cache.pkl', 'wb'))
        cache = pickle.load(open('cache.pkl', 'rb'))


def update_cache(d: dict):
    cache.update(d)
    pickle.dump(cache, open('cache.pkl', 'wb'))


def main():
    stickers = []
    for path, folders, files in os.walk('stickers'):
        if path.endswith('/'):
            path = path[10:]
        else:
            path = path[9:]
        for sticker in files:
            sticker = sticker[:-4].encode('utf-8').replace(b'\xb8\xcc\x86', b'\xb9').decode('utf-8')
            if path:
                stickers.append(f'{path}.{sticker}')
            else:
                stickers.append(sticker)

    with open('config.json', 'r') as f:
        config = json.load(f)

    if config['token']:
        session = VkApi(token=config['token'], api_version='5.89',
                        captcha_handler=captcha_handler)
    else:
        session = VkApi(login=config['login'], password=config['password'],
                        api_version='5.89', captcha_handler=captcha_handler)
        try:
            session.auth()
        except ApiError:
            print(traceback.format_exc())
            exit()
    api = session.get_api()

    if len(stickers) == 0:
        print('No stickers initialized!')
        exit()
    lp = VkLongPoll(session)
    up = VkUpload(session)
    open_cache()
    print(f'Initialized {len(stickers)} stickers ({len(cache)} cached)')
    for event in lp.listen():
        if event.type == VkEventType.MESSAGE_NEW and \
                event.from_me and event.text.startswith('!') and event.text.endswith('!') and \
                event.text[1:-1] in stickers:
            if event.text[1:-1] in cache:
                sticker = cache[event.text[1:-1]]
            else:
                sticker = up.graffiti('stickers/' + event.text[1:-1].replace('.', '/') + '.png', event.peer_id)[0]
                sticker = f'doc{sticker["owner_id"]}_{sticker["id"]}'
                update_cache({event.text[1:-1]: sticker})
            vk_send_sticker(api, event.message_id, event.peer_id, sticker)

try:
    main()
except KeyboardInterrupt:
    print('Shutting down...')
