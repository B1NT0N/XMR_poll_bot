import requests
from bs4 import BeautifulSoup as soup
from datetime import datetime
from threading import Thread,Lock
from time import sleep
from dotenv import load_dotenv
import os
import json


load_dotenv('.env')
wallet = os.getenv('WALLET')
url = "https://web.xmrpool.eu:8119/stats_address"

def get_data(wallet):
    params = {"address": f"{wallet}",
            "longpoll": "false"
            }
    response = requests.get(url,params)
    
    data = response.json()
    return data

token = os.getenv('BOT_TOKEN')
config={'url':f"https://api.telegram.org/bot{token}",'lock':Lock()}

msg = ''
old_msg=""
new_msg = ''
def del_updates(data):
    config['lock'].acquire()
    requests.post(f"{config['url']}/getUpdates",{'offset':data["update_id"]+1})
    config['lock'].release()

def send_message_only(data, msg):
    config['lock'].acquire()

    send_data = {"chat_id":data["message"]["chat"]["id"],
                "text":str(msg),
                "parse_mode":"Markdown"
    }

    requests.post(f"{config['url']}/sendMessage",send_data)
    config['lock'].release()

def send_keyboard_message(data,msg):
    config['lock'].acquire()


    keyboard = {
                "keyboard":[
                            [
                                {"text": "⛏ Your Mining Statistics"}
                            ],
                            [
                                {"text": "🤖 Your Workers / Rigs"}
                            ]
                        ],
                'resize_keyboard':True,
                "one_time_keyboard":False
                }

    keyboard = json.dumps(keyboard)

    send_data = {"chat_id":data["message"]["chat"]["id"], 
                "text":str(msg),
                "reply_markup":keyboard
    }

    #print(send_data)
    requests.post(f"{config['url']}/sendMessage",send_data)
    config['lock'].release()

print("Bot Started")
while True:

    json_load=''
    while 'result' not in json_load:
        try:
            json_load = json.loads(requests.get(f"{config['url']}/getUpdates").text)
        except Exception as exception:
            json_load = ''
            if 'Failed to establish a new connection' in str(exception):
                print("Connection failed")
            else:
                print(f"Unknow Error: {exception}")

    if len(json_load["result"]) > 0:
        for data in json_load["result"]:
            del_updates(data,)
            try:
                new_msg = data["message"]["text"]
            except Exception as exception:
                send_keyboard_message(data, "Unsuported Data Type")
                
            if new_msg == "/start":
                send_message_only(data, "Welcome")
                send_message_only(data, "Please use /config to configure the bot")
            if new_msg == "/config":
                send_message_only(data,"Please send me your XMR Address")
                
            if old_msg == "/config" and len(new_msg) == 95:
                wallet = new_msg
                send_keyboard_message(data,"XMR Address Configurated Sucesfully")
            elif old_msg == "/config" and len(new_msg) != 95:  
                send_message_only(data,"Invalid Address")
                send_message_only(data, "Please Use /config to configure the bot")
            
            if new_msg == "⛏ Your Mining Statistics":
                mining_data = get_data(wallet)
                send_message_only(data,
                                  "*BALANCE*\n"
                                  f'🏦 Pending Balance: {str(float(mining_data["stats"]["balance"])/10**12) if ("balance" in mining_data["stats"]) is True else "0.000000000000"}\n'
                                  f'💳 Last Block Reward: {str(float(mining_data["stats"]["last_reward"])/10**12) if ("last_reward" in mining_data["stats"]) is True else "0.000000000000"}\n'
                                  f'💵 Total Paid: {str(float(mining_data["stats"]["total_paid"])/10**12) if "last_reward" in mining_data["stats"] is True else "0.000000000000"}\n'
                                  '\n*PERFORMANCE*\n'
                                  f'🕘 Last Share Submitted: {datetime.fromtimestamp(int(mining_data["stats"]["lastShare"])).strftime("%H:%M") if ("lastShare" in mining_data["stats"]) is True else "Never"}\n'
                                  f'📤 Total Hashes Submitted: {mining_data["stats"]["hashes"] if ("hashes" in mining_data["stats"]) is True else "0"}\n'
                                  f'⏱ Hash Rate: {mining_data["stats"]["hashrate"] if ("hashrate" in mining_data["stats"]) is True else "0 H"}/sec'
                                  )
            if new_msg == "🤖 Your Workers / Rigs":
                # send_message_only(data,"Coming Soon")
                mining_data = get_data(wallet)
                for worker in mining_data["perWorkerStats"]:
                    send_message_only(data,
                                  f'*PER WORKER STATS*\n'
                                  f'🗝 Worker / Rig ID: *{worker["workerId"]}*\n'
                                  f'⏱ Hash Rate: {worker["hashrate"] if ("hashrate" in worker) is True else "0 H"}/sec\n'
                                  f'📤 Accepted Hashes: {worker["hashes"] if ("hashes" in worker) is True else "0"}\n'
                                  f'🕘 Last Share: {datetime.fromtimestamp(int(worker["lastShare"])).strftime("%H:%M") if ("lastShare" in worker) is True else "Never"}\n'
                                  )
                
            old_msg = new_msg 
            # msg=f'{data["message"]["text"]} from: BOT'
            # print(f'{data["message"]["text"]} from: {data["message"]["chat"]["username"]}')

        sleep(1)