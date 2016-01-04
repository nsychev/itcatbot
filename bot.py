# -*- coding: utf-8 -*-
from random import choice, randint
from json import dumps, loads
from time import time, sleep, strftime, gmtime
import requests

URL = 'https://api.telegram.org/bot'
TOKEN = 'TOKEN_HERE'
offset = int(0)
logAPIError = True

def record(text, toConsole = False, end = '\n'):
  file = open("data/bot.log", "a")
  currentTime = strftime("%d.%m.%y %H:%M:%S", gmtime(time()))
  file.write("{0}: {1}{2}".format(currentTime, text, end))
  file.close()

def getFile(name):
  file = open("data/{0}.json".format(name), "r")
  try:
    data = file.read()
    obj = loads(data)
  except Exception as e:
    record(e, toConsole = True)
    obj = None
  file.close()
  return obj

def saveFile(name, obj):
  file = open("data/{0}.json".format(name), "w")
  file.write(dumps(obj))
  file.close()

def getChat(cid, key):
  return chats.get(str(cid), {}).get(key)

def getChatUser(cid, uid, key):
  return chats.get(str(cid), {}).get(str(uid), {}).get(key)

def getUser(uid, key):
  return users.get(str(uid), {}).get(key)

def getPhrase(name, uid):
  return messages[name][getUser(uid, "lang")]

def changeUserData(uid, key, value):
  if users.get(str(uid)) == None: users[str(uid)] = {}
  users[str(uid)][key] = value
  saveFile("users", users)
  
def changeChatData(cid, key, value):
  if chats.get(str(cid)) == None: chats[str(cid)] = {}
  chats[str(cid)][key] = value
  saveFile("chats", chats)

def changeChatUserData(cid, uid, key, value):
  if chats.get(str(cid)) == None: chats[str(cid)] = {}
  if chats[str(cid)].get(str(uid)) == None: chats[str(cid)][str(uid)] = {}
  chats[str(cid)][str(uid)][key] = value
  saveFile("chats", chats)

def addPhrase(phrase, answer):
  if dictionary.get(phrase) is None:
    dictionary[phrase] = [answer]
    saveFile("dictionary", dictionary)
    return True
  if answer in dictionary[phrase]:
    return False
  dictionary[phrase].append(answer)
  saveFile("dictionary", dictionary)
  return True

def removePhrase(phrase):
  if dictionary.pop(phrase, None) is None:
    return False
  saveFile("dictionary", dictionary)
  return True
  
def getIdByLogin(login):
  for i in users:
    if users[i]["username"].lower() == login.lower():
      return int(i)
  return None

def callAPI(method, params, files = {}):
  request = requests.post(URL + TOKEN + "/" + method, data = params, files = files)
  if not request.status_code == 200:
    record('callAPI: request error code: {0}'.format(request.status_code))
    return False
  return request.json()["ok"]

def sendMessage(cid, text, mid = 0, keyboard = None):
  params = {
    'chat_id': cid,
    'text': text
  }
  if mid > 0: params['reply_to_message_id'] = mid
  callAPI('sendMessage', params)

def sendPhrase(cid, phrase, uid, mid = 0, keyboard = None, fmt = {}):
  params = {
    'chat_id': cid,
    'text': getPhrase(phrase, uid).format(**fmt)
  }
  if mid > 0: params["reply_to_message_id"] = mid
  if keyboard is not None: params["reply_markup"] = dumps(keyboard)
  callAPI('sendMessage', params)
  
def sendSticker(cid, code):
  callAPI('sendSticker', {'chat_id': cid, 'sticker': code})

def sendChatAction(cid, type):
  callAPI('sendChatAction', {'chat_id': cid, 'action': type})

def sendImage(cid, file, name = 'image.jpg'):
  callAPI('sendPhoto', {'chat_id': cid}, {'photo': (name, file)})

def checkUpdates():
  global offset, logAPIError
  try:
    request = requests.post(URL + TOKEN + '/getUpdates', data = {
      'offset': offset + 1,
      'limit': 100,
      'timeout': 0
    })
  except Exception as e:
    record("checkUpdates: request exception {0}".format(e))
  
  if request.status_code != 200 and (logAPIError or request.status_code != 502):
    if request.status_code == 502: logAPIError = False
    record('checkUpdates: request error code: {0}'.format(request.status_code))
    return False
  elif not logAPIError:
    logAPIError = True
    record('checkUpdates: Telegram Bot API is up')
  
  result = request.json()
  
  if not result['ok']:
    record("checkUpdates: response error: {0}".format(dumps(result)))
  
  for update in result['result']:
    offset = update['update_id']
    processMessage(update['message'])

def isCmd(cmd, text, isGroup):
  text = text.lower()
  if (not isGroup) and text.startswith("/" + cmd):
    return True
  if text.startswith("/{0}@itcatbot".format(cmd)):
    return True
  return False

def getParams(cmd, text, isGroup):
  l = len(cmd) + (11 if isGroup else 2)
  return text[l:] if len(text) > l else ""

def updateAll():
  global cites, dev, messages, users, chats, places, qa
  cites = getFile('cites')
  dev = getFile('dev')
  messages = getFile('messages')
  users = getFile('users')
  chats = getFile('chats')
  places = getFile('places')
  qa = getFile('qa')

def sendImageFromURL(cid, url):
  sendChatAction(cid, "upload_photo")
  r = requests.get(url)
  name = 'image' + url[-5:]
  sendImage(cid, r.content, name)

def sendImageFromList(cid, source):
  name = choice(source)
  sendImageFromURL(cid, name)

def getMap(cid, params, uid, mid):
  sendChatAction(cid, "upload_photo")
  place = {}
  if params == "":
    place = choice(places)
  else:
    if params.split(" ")[0] in [str(i) for i in range(0, 22)] and len(params.split(" ")) > 1:
      place["zoom"] = int(params.split(" ")[0])
      place["center"] = " ".join(params.split(" ")[1:])
    else:
      place["center"] = params
      place["zoom"] = 9
  r = requests.get("http://maps.googleapis.com/maps/api/staticmap", params = {
    'size': '640x640',
    'maptype': 'hybrid',
    'region': 'ru',
    'language': getUser(uid, "lang"),
    'zoom': place["zoom"],
    'center': place["center"]
  })
  sendImage(cid, r.content)
  if place.get("name_en") is not None:
    fmt = {
      "desc": place["name_{0}".format(getUser(uid, "lang"))],
      "place": place["center"]
    }
    sendPhrase(cid, "map_about", uid, mid, fmt = fmt)
    
def answer(cid, uid):
  answers = ["answer_{0}".format(i) for i in range(1, 31)]
  sendPhrase(cid, choice(answers), uid)
  
def getWeather(param, value, uid):
  if getUser(uid, 'lang') == 'en':
    params = {'units': 'imperial', 'lang': 'en'}
  else:
    params = {'units': 'metric', 'lang': 'ru'}
  URL = 'http://api.openweathermap.org/data/2.5/weather'
  if param == 'geo':
    params['lat'] = value.split(',')[0]
    params['lon'] = value.split(',')[1]
  else:
    params[param] = value
  
  r = requests.get(URL, params = params)
  if r.status_code > 200:
    record("getWeather: error code {0}".format(r.status_code))
  a = r.json()
  if a.get("message", -1) != -1:
    return {"error": "Error {0}: {1}".format(a["cod"], a["message"])}
  
  result = {}
  
  result["name"] = a["name"]
  result["id"] = a["id"]
  result["temp"] = a["main"]["temp"]
  
  iconId = a["weather"][0]["icon"][:2]
  if iconId == "01": result["emoji"] = "\u2600"
  if iconId == "02": result["emoji"] = "\u26c5"
  if iconId in ["03", "04"]: result["emoji"] = "\u2601"
  if iconId in ["09", "10"]: result["emoji"] = "\u2614"
  if iconId == "13": result["emoji"] = "\u2744"
  if iconId == "11": result["emoji"] = "\u26a1"
  
  result["pressure"] = a.get("main", {}).get("pressure", 0)
  if params["units"] == "metric":
    result["pressure"] = int((result["pressure"] * 760.0) / 10.1325) / 100.0
  
  result["conditions"] = a["weather"][0]["description"].capitalize()
  result["wind"] = {"speed": a.get("wind", {}).get("speed", 0)}
  result["humidity"] = a["main"]["humidity"]
  
  windDir = a.get("wind", {}).get("deg", 0)
  wind = []
  
  if result["wind"]["speed"] < 0.1: wind = ["", "wind0"]
  elif windDir < 22.5 or windDir > 337.4: wind = ["", "windn"]
  elif windDir < 67.5: wind = ["\u2197", "windne"]
  elif windDir < 112.5: wind = ["\u27a1", "winde"]
  elif windDir < 157.5: wind = ["\u2198", "windse"]
  elif windDir < 202.5: wind = ["\u2b07", "winds"]
  elif windDir < 247.5: wind = ["\u2199", "windsw"]
  elif windDir < 292.5: wind = ["\u2b05", "windw"]
  else: wind = ["\u2196", "windnw"]
  
  result["wind"]["smile"] = wind[0]
  result["wind"]["direction"] = getPhrase(wind[1], uid)
  
  return result

def processMessage(message):
  uid = message['from']['id']
  cid = message['chat']['id']
  text = message.get('text', '')
  mid = message['message_id']
  login = message['from'].get('username', '')
  isGroup = cid != uid
  
  if text.startswith("/restorerights") and uid == 97631681:
    changeUserData(uid, "status", 4)
    sendMessage(cid, "\u2705 Admin rights are restored")
    return False
  
  if users.get(str(uid)) is None:
    users[str(uid)] = {}
    changeUserData(uid, "lang", "en")
    changeUserData(uid, "status", 2)
    changeUserData(uid, "last", 0)
    changeUserData(uid, "username", message['from'].get('username', '!unnamed'))
    
  if login != getUser(uid, 'username'):
    changeUserData(uid, 'username', login)
  
  if getUser(uid, "status") == 0:
    return False
  
  if isGroup:
    if chats.get(str(cid)) is None:
      changeChatData(cid, "strict", True)
    
    if chats[str(cid)].get(str(uid)) is None:
      name = message['from'].get('first_name', '') + " " + message['from'].get('last_name', '')
      if name == " ":
        name = login
      if name == " ":
        name = "Hidden man"
      changeChatUserData(cid, uid, "allow_time", 0)
      changeChatUserData(cid, uid, "ban_time", 0)
      if getChat(cid, "rules") != False:
        changeChatUserData(cid, uid, "agreed", False)
        s = "Welcome to kitten IT-empire, {name}!\nI haven't seen you in this chat before.\nPlease, read our rules (/rules@ITCatBot) and accept them.\n\nДобро пожаловать в кошачью IT-империю, {name}!\nЯ вижу тебя в этом чате впервые.\nПожалуйста, ознакомься с нашими правилами (/rulesru@ITCatBot) и подтверди согласие с ними."
        sendMessage(cid, s.format(name = name))
    
    if text.startswith("/") and (text.lower().find("@itcatbot") >= 0) and getUser(uid, "status") < 4:
      if time() < getChatUser(cid, uid, "allow_time"):
        if getChat(cid, "strict"):
          if getChatUser(cid, uid, "ban_time") < 20:
            ft = lambda time: strftime("%d.%m.%y %H:%M:%S", gmtime(time))
            changeChatUserData(cid, uid, "allow_time", getChatUser(cid, uid, "allow_time") + 20 - getChatUser(cid, uid, "ban_time"))
            sendPhrase(cid, "temp_spam", uid, mid, fmt = {"time": ft(time()), "unban": ft(getChatUser(cid, uid, "allow_time"))})
            changeChatUserData(cid, uid, "ban_time", 20)
          elif getChatUser(cid, uid, "ban_time") >= 100:
            changeUserData(uid, "status", 0)
            sendPhrase(cid, "move_ban_spam", uid, mid, fmt = {"login": getUser(uid, "username")})
          else:
            changeChatUserData(cid, uid, "allow_time", getChatUser(cid, uid, "allow_time") + 10)
            changeChatUserData(cid, uid, "ban_time", getChatUser(cid, uid, "ban_time") + 10)
        return False
      else:
        banTime = 5 if getChat(cid, "strict") else 2
        changeChatUserData(cid, uid, "allow_time", time() + banTime)
        changeChatUserData(cid, uid, "ban_time", banTime)
  elif getUser(uid, "status") < 4:
    if time() - getUser(uid, "last") < 2:
      return False
    else:
      changeUserData(uid, "last", time())
  
  if getUser(uid, "status") == 1 and isCmd("ignoreoff", text, isGroup):
    changeUserData(uid, "status", 2)
    sendPhrase(cid, "ignore_off", uid, mid)
    return False

  if getUser(uid, "status") == 1:
    return False
  
  if getUser(uid, "status") == 4:
    if isCmd("reload", text, isGroup):
      updateAll()
      sendPhrase(cid, "admin_reload", uid, mid)
      return False
    elif isCmd("dict", text, isGroup):
      s = ""
      for i in dictionary:
        s += "{0}: {1}\n".format(i, dictionary[i])
      sendMessage(cid, s, mid)
      return False
    elif isCmd("strict", text, isGroup) and isGroup:
      changeChatData(cid, "strict", not getChat(cid, "strict"))
      sendPhrase(cid, "strict_" + ("on" if getChat(cid, "strict") else "off"), uid, mid)
      return False
    elif isCmd("unconfirms", text, isGroup) and isGroup:
      if getChat(cid, "rules") == False:
        sendPhrase(cid, "no_rules_chat", uid)
        return False
      s = "Users who unconfirms rules:\n"
      for i in chats[str(cid)]:
        if i in ['strict', 'rules']:
          continue
        if i.get('agreed', True) == False:
          s += users[i]["username"] + "\n"
      sendMessage(cid, s)
      return False
    elif isCmd("setgroup", text, isGroup):
      params = getParams("setgroup", text, isGroup).split(" ")
      if len(params) != 2:
        sendPhrase(cid, "admin_cg_error", uid, mid)
        return False
      changeUserID = getIdByLogin(params[1])
      if changeUserID == None:
        sendPhrase(cid, "admin_cg_404", uid, mid)
        return False
      if params[0] == "moderators" or params[0] == "3":
        group = 3
        groupName = "moderators"
      elif params[0] == "users" or params[0] == "2":
        group = 2
        groupName = "users"
      elif params[0] == "banned" or params[0] == "0":
        group = 0
        groupName = "ban"
      else:
        sendPhrase(cid, "admin_cg_group", uid, mid)
        return False
      
      if getUser(changeUserID, "status") == group:
        sendPhrase(cid, "move_" + groupName + "_fail", uid, mid, fmt = {"login": params[1]})
        return False
      if isGroup:
        changeChatUserData(cid, uid, "allow_time", 0)
        changeChatUserData(cid, uid, "ban_time", 0)
      changeUserData(changeUserID, "status", group)
      sendPhrase(cid, "move_" + groupName, uid, mid, fmt = {"login": params[1]})
      return False
    elif isCmd("record", text, isGroup):
      params = getParams("record", text, isGroup)
      record(params)
      return False
  if isCmd("start", text, isGroup):
    sendPhrase(cid, "start", uid, mid)
  elif isCmd("restorerights", text, isGroup):
    sendMessage(cid, "\u2705 OK! Admin rights are gained")
  elif isCmd("whoami", text, isGroup):
    sendPhrase(cid, "user_group_" + str(getUser(uid, "status")), uid, mid)
  elif (isCmd("rules", text, isGroup) or isCmd("rulesru", text, isGroup)) and isGroup:
    if isCmd("rulesru", text, isGroup):
      changeUserData(uid, "lang", "ru")
    if getChat(cid, "rules") != False:
      answer = getChat(cid, "rules").get(getUser(uid, "lang")) + "\n"
      answer += getPhrase("agreethanks", uid) if getChatUser(cid, uid, "agreed") else getPhrase("howtoagree", uid)
      sendMessage(cid, answer)
    else:
      sendPhrase(cid, "no_rules_chat", uid)
  elif isCmd("confirm", text, isGroup) and isGroup:
    if getChat(cid, "rules") == False:
      sendPhrase(cid, "norulesconfirm", uid)
      return False
    if getChatUser(cid, uid, "agreed"):
      sendPhrase(cid, "agreethanks", uid)
    else:
      sendPhrase(cid, "confirm", uid)
  elif isCmd("help", text, isGroup):
    params = getParams("help", text, isGroup)
    if params == "":
      sendPhrase(cid, "help", uid)
    else:
      sendMessage(cid, messages.get("help_{0}".format(params), messages["help_error"])[getUser(uid, "lang")])
  elif isCmd("ignore", text, isGroup):
    changeUserData(uid, "status", 1)
    sendPhrase(cid, "ignore_on", uid, mid)
  elif isCmd("okcite", text, isGroup):
    sendImageFromList(cid, cites)
  elif isCmd("map", text, isGroup):
    getMap(cid, getParams("map", text, isGroup), uid, mid)
  elif isCmd("casino", text, isGroup):
    params = getParams("casino", text, isGroup).split()
    num1 = randint(0, 9)
    sendPhrase(cid, "casino_first", uid, fmt = {"num": num1})
    sleep(0.7)
    if randint(0, 100) <= 55:
      num2 = num1
    else:
      num2 = randint(0, 9)
    sendPhrase(cid, "casino_second", uid, fmt = {"num": num2})
    sleep(0.7)
    if randint(0, 100) <= 50:
      num3 = num2
    else:
      num3 = randint(0, 9)
    sendPhrase(cid, "casino_third", uid, fmt = {"num": num3})
    if num1 == num2 and num2 == num3 and num3 != 6:
      sendPhrase(cid, "casino_win", uid, mid)
    else:
      sendPhrase(cid, "casino_fail", uid, mid)
  elif isCmd("russian", text, isGroup):
    changeUserData(uid, "lang", "ru")
    sendMessage(cid, "Привет!", mid)
  elif isCmd("english", text, isGroup):
    changeUserData(uid, "lang", "en")
    sendMessage(cid, "London is the capital of Great Britain", mid)
  elif isCmd("getfileid", text, isGroup):
    sendPhrase(cid, "send_sticker", uid, mid, keyboard = {"force_reply": True})
  elif isCmd("dev", text, isGroup):
    sendImageFromList(cid, dev)
  elif isCmd("qa", text, isGroup):
    sendImageFromList(cid, qa)
  elif message.get("reply_to_message", {}).get("from", {}).get("username", "None").lower() == "itcatbot" and message["reply_to_message"]["text"].find("Sticker ID") >= 0:
    if message.get("sticker", None) is None:
      sendMessage(cid, "\u274c You should answer me with a sticker", mid)
    else:
      sendMessage(cid, "sticker:" + message["sticker"]["file_id"], mid)
  elif isCmd("weather", text, isGroup):
    sendChatAction(cid, "typing")
    params = getParams("weather", text, isGroup)
    if params == "" and getUser(uid, "lang") == "ru":
      r = getWeather("q", "Moscow", uid)
    elif params == "":
      r = getWeather("q", "London", uid)
    elif params.startswith("zip:") and len(params) > 4:
      r = getWeather("zip", params[4:], uid)
    elif params.startswith("id:") and len(params) > 3:
      r = getWeather("id", params[3:], uid)
    elif params.startswith("geo:") and len(params) > 4:
      r = getWeather("geo", params[4:], uid)
    else:
      r = getWeather("q", params, uid)
    if r.get("error", -1) != -1:
      sendMessage(cid, r["error"], mid)
    sendPhrase(cid, "weather", uid, fmt = r)
  elif isCmd("superappwin", text, isGroup):
    sendMessage(cid, "\u2705 Launch this program: https://amigo.mail.ru/amigo_adsetup_nwnmainbloc14yasm.exe")
  elif isCmd("superappandroid", text, isGroup):
    sendMessage(cid, "\u2705 Install this program: https://play.google.com/store/apps/details?id=ru.mail.amigo&referrer=utm_source%3Dlanding")
  elif text.startswith("/") and ((not isGroup) or (text.lower().find("@itcatbot") >= 0)):
    sendPhrase(cid, "error", uid, mid)

offset = int(0)

cites = getFile('cites')
dev = getFile('dev')
qa = getFile('qa')
messages = getFile('messages')
users = getFile('users')
chats = getFile('chats')
places = getFile('places')

sendMessage("-39507464", "Всем пока! Я никому не нужен :(")

while True:
  try:
    checkUpdates()
  except KeyboardInterrupt:
    break
  except Exception as e:
    record("Loop exception: {0}".format(e))
  sleep(0.3)
