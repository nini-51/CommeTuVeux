import paho.mqtt.client as mqtt
from datetime import datetime
import requests, json
import threading
import sys, os
import time

lock = threading.Lock()
request = []
broker = "mosquitto"

# Load env vars
try:
    WAREHOUSE_ID = os.environ['WAREHOUSE_ID']
except KeyError:
    print(f'[error]: `WAREHOUSE_ID` environment variable required')
    sys.exit(1)

try:
    API_SERVER = os.environ['API_SERVER']
except KeyError:
    print(f'[error]: `API_SERVER` environment variable required')
    sys.exit(1)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("test")


# | Package-id
# 	|  warehouse_id
# 	| timestanp (iso 8601)
# 	| satus
# 		|_> in transit
def do_json(client, userdata, msg):
    # get current datetime and transforme to right iso 8601
    today = datetime.now()
    date = today.isoformat()

    B = [str(x) for x in str(msg.payload).split(',') if x.strip()]
    a=(json.dumps({'warehouse_id': WAREHOUSE_ID, 'timestamp' : date, 'status' : B[2]}, sort_keys=True, indent=4))
    print(a)

    #block ressource
    lock.acquire()
    if B[2]=="init":
        request.append("post")
    elif(B[2]=="update"):
        request.append("put")
    else:
        exit("Etat inconnu")
    request.append(f"http://{API_SERVER}:5000/objects/"+str(B[1]))
    request.append(a)
    #debloque ressource
    lock.release()

#fonction multi-threadee
def test_connexion():
    while(True):
        r=requests.get(f'http://{API_SERVER}:5000')

        if (r.status_code == requests.codes.ok):
            lock.acquire()
            while(request):
                if(request[0]==post):
                    #POST
                    r = requests.post(request[1], data=request[2])
                else:
                    #PUT
                    r= requests.put(request[1],data=request[2])
                del request[0:3]
            lock.release()
        sleep(1)



# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

    message = do_json(client, userdata, msg)

    #thread pour double connexion
    x=threading.Thread(target=test_connexion)
    # threads.append(x)
    x.start()


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker, 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
