import requests
from datetime import datetime
from threading import Thread,Lock
from time import sleep
from dotenv import load_dotenv
import os
import json
import mysql.connector

load_dotenv('.env')

#MySQL Variables Config
USERNAME= os.getenv('MSQL_USERNAME')
DATABASE_NAME= os.getenv('MSQL_DATABASE_NAME')
PASSWORD= os.getenv('MSQL_PASSWORD')
SERVER= os.getenv('MSQL_SERVER')
PORT= os.getenv('MSQL_PORT')

mydb = mysql.connector.connect(
    host=f"{SERVER}",
    user=f"{USERNAME}",
    password=f"{PASSWORD}",
    database=f"{USERNAME}"
)

#Telegram Variables Config
msg = ''
old_msg=""
new_msg = ''

#XMR Pool Variables Config

wallet = None
url = "https://web.xmrpool.eu:8119/stats_address"

#Telegram Bot Config
token = os.getenv('BOT_TOKEN')
config={'url':f"https://api.telegram.org/bot{token}",'lock':Lock()}

#Search For Wallet
def get_wallet(mydb,chat_id):
    mycursor = mydb.cursor()
    
    mycursor.execute("SELECT * FROM customers")

    myresult = mycursor.fetchall()

#Insert Into Table
def insert_wallet(mydb,chat_id,wallet):
    mycursor = mydb.cursor()
    sql = f"INSERT INTO {DATABASE_NAME} (chat_id, wallet_address) VALUES (%s, %s)"
    val = (chat_id, wallet)
    mycursor.execute(sql, val)

    mydb.commit()

#Receive The Wallet and Return the Data
def get_data(wallet):
    
    params = {"address": f"{wallet}",
            "longpoll": "false"
            }
    response = requests.get(url,params)
    
    data = response.json()
    return data

#Get Last Message From Telegram
def del_updates(data):
    config['lock'].acquire()
    requests.post(f"{config['url']}/getUpdates",{'offset':data["update_id"]+1})
    config['lock'].release()

#Send Standart Message On Telegram
def send_message_only(data, msg):
    config['lock'].acquire()

    send_data = {"chat_id":data["message"]["chat"]["id"],
                "text":str(msg),
                "parse_mode":"Markdown"
    }

    requests.post(f"{config['url']}/sendMessage",send_data)
    config['lock'].release()

#Set the Keyboard Message On Telegram
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
    #Try To Establish Connection With Telegram API
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
    #Get The Last Message from Telegram
    if len(json_load["result"]) > 0:
        for data in json_load["result"]:
            del_updates(data,)
            try:
                new_msg = data["message"]["text"]
            except Exception as exception:
                send_keyboard_message(data, "Unsuported Data Type")
            
            #/START COMMAND    
            if new_msg == "/start":
                send_message_only(data, "Welcome")
                send_message_only(data, "Please use /help for instruction on how to use the bot")
            
            #/CONFIG COMMAND    
            if new_msg == "/config":
                send_message_only(data,"Please send me your XMR Wallet Address")
                
            #/CONTACT COMMAND    
            if new_msg == "/contact":
                send_message_only(data,"DM me at @B1NT0N")
                
            #/DONATE COMMAND    
            if new_msg == "/donate":
                send_message_only(data,"XMR Wallet Address: `47hMEVicDHdTGwcyTiQair3ong6v1yQAUQKLCdbYt41sXnA3mCaDBfNjgWMF9GdF24XR1b97VBNgMZ64UxB5iTrUHAnAPKe`")
            
            if new_msg == "0":
                insert_wallet(mydb,data["message"]["chat"]["id"],1)
            
            #/HELP COMMAND    
            if new_msg == "/help":
                send_message_only(data,
                                  "*HELP*\n"
                                  "/config - *CONFIGURE* the bot\n"
                                  "/help - *HELP*\n"
                                  "/donate - *GIVE CREDITS* to the creator\n"
                                  "/contact - inform on *BUGS* or *FEATURES*\n"
                                  )
                
            #Check if Configuration is Valid    
            if old_msg == "/config" and len(new_msg) == 95:
                wallet = new_msg
                insert_wallet(mydb,data["message"]["chat"]["id"],wallet)
                send_keyboard_message(data,"✔ XMR Address Configurated Sucesfully")
            elif old_msg == "/config" and len(new_msg) != 95:  
                send_message_only(data,"❌ Invalid Address")
                send_message_only(data, "Please Use /config to configure the bot")
            
            #if wallet is not None:
            #Send Mining Statistics Information
            if new_msg == "⛏ Your Mining Statistics" and wallet is not None:
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
            elif new_msg == "⛏ Your Mining Statistics" and wallet is None:
                send_message_only(data,"Oops! Something happened and I can't remember your XMR Wallet Address")
                send_message_only(data, "Please Use /config to reconfigure the bot")
                
            
            #Send Your Workers / Rigs Information    
            if new_msg == "🤖 Your Workers / Rigs" and wallet is not None:
                mining_data = get_data(wallet)
                for worker in mining_data["perWorkerStats"]:
                    send_message_only(data,
                                f'*PER WORKER STATS*\n'
                                f'\n🗝 Worker / Rig ID: *{worker["workerId"]}*\n'
                                f'⏱ Hash Rate: {worker["hashrate"] if ("hashrate" in worker) is True else "0 H"}/sec\n'
                                f'📤 Accepted Hashes: {worker["hashes"] if ("hashes" in worker) is True else "0"}\n'
                                f'🕘 Last Share: {datetime.fromtimestamp(int(worker["lastShare"])).strftime("%H:%M") if ("lastShare" in worker) is True else "Never"}\n'
                                )
            elif new_msg == "🤖 Your Workers / Rigs" and wallet is None:
                send_message_only(data,"Oops! Something happened and I can't remember your XMR Wallet Address")
                send_message_only(data, "Please Use /config to reconfigure the bot")
                
            old_msg = new_msg 
        sleep(1)