import network
import time
import utime
from umqtt.simple import MQTTClient
import ubinascii
import random
import math
import machine

import M5 
from M5 import Widgets

SERVER = "192.168.138.238"
CLIENT_ID = ubinascii.hexlify(machine.unique_id())

DATA_TOPIC = f"IOT/Data/{CLIENT_ID.decode()}"
SUBSCRIBE_TIME = "IOT/Time/GlobalNetworkTime"
CONNECT_PATH = "IOT/Connect"
ACK_CONNECT_PATH = "IOT/AckConnect"
STORM_PATH = "IOT/Server/Storm"
ANOMALY_PATH = "IOT/Server/Anomaly"
IRRIGATION_PATH = "IOT/Server/Irrigation"

last_fetched_time = None
is_conn = False

def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    print('Network config:', wlan.ifconfig())
    return (wlan)

def set_local_time_from_timestamp(timestamp):
    global last_fetched_time
    dt = utime.localtime(timestamp)
    time_tuple = (dt[0], dt[1], dt[2], 0, dt[3], dt[4], dt[5], 0)
    machine.RTC().datetime(time_tuple)
    print(f"Synced time")
    last_fetched_time = utime.mktime(utime.localtime())
    
def subscribe_callback(topic, msg):
    print(topic,msg)
    global is_conn
    if(topic.decode() == SUBSCRIBE_TIME):
        set_local_time_from_timestamp(int(msg.decode()))
        
    if(topic.decode() == ACK_CONNECT_PATH):
        print(topic, msg)
        if msg.decode().split(' ')[-1] == CLIENT_ID.decode():
            is_conn = True
            print("Received response from central client")
            
    if(topic.decode() == STORM_PATH):
        if (msg.decode().split(' :: ')[0] == "True"):
            print("Storm")  
            M5.Speaker.tone(4000,500)
            time.sleep(0.5)
            M5.Speaker.tone(4000,500)
            time.sleep(0.5)
            M5.Speaker.tone(4000,500)
            Widgets.Title("Storm Incoming", 32)
            time.sleep(2)
            M5.Display.clear(0)
            
    if(topic.decode() == IRRIGATION_PATH):
        if (msg.decode().split(' :: ')[0] == "[1]"):
            print("Irrigation")
            Widgets.fillScreen(0xFF0000)
            Widgets.Title("Irrigate", 32)
            time.sleep(2)
            M5.Display.clear(0)
            
    if(topic.decode() == ANOMALY_PATH):
        if (msg.decode().split(' :: ')[0] == "True"):
            print("Anomaly")
            M5.Speaker.tone(5000,500)
            Widgets.Title("Some Anomaly", 32)
            time.sleep(2)
            M5.Display.clear(0)
    

    print("Received: "+str((topic.decode(), msg.decode())))
    
#==========================================================================================
#==========================================================================================
def gen_soil_moisture(t):
    sm = None
    if t<18:
        sm = math.exp(-t / 5) * (5/6) 
    else:
        sm = math.exp((-(t-25)**2)/10)
    
    return math.sqrt(213.65) * sm + 44.78 + 0.5*random.random()

def gen_air_moisture(t):
    sm = None
    if t<18:
        sm = math.exp(-t / 5) * (5/6) 
    else:
        sm = math.exp((-(t-25)**2)/10)
    
    return math.sqrt(900) * sm + 58 + 0.5*random.random()

def gen_wind_speed(t):
    ws = None
    if (t<45):
        ws = 1/ (1 + math.exp(-t/10 + 1))

    elif (t<65):
        ws = 1/ (1 + math.exp(-50/10 + 1))

    else:
        ws = 1/ (1 + math.exp(t/10 - 10))

    return ws*math.sqrt(647)+ 42.2 + 0.5*random.random()

def getSensorData(T):
    t = T%110  
    wind_speed = gen_wind_speed(t)
    
    t = T%27
    soil_moisture = gen_soil_moisture(t)
    air_moisture = gen_air_moisture(t)

    mean_water_depth = 5  
    std_dev_water_depth = 1  

    mean_solar_radiation = 500 
    std_dev_solar_radiation = 200  

    mean_wind_direction = 180 
    std_dev_wind_direction = 90 

    water_depth = std_dev_water_depth* random.random() + mean_water_depth
    solar_radiation = std_dev_solar_radiation* random.random() + mean_solar_radiation
    wind_direction = std_dev_wind_direction* random.random() + mean_wind_direction


    wind_direction = wind_direction % 360

    
    air_temperature_mean = 24.26
    air_temperature_variance = 40
    air_temperature = math.sqrt(air_temperature_variance) * random.random() + air_temperature_mean

    ph_mean = 6.49
    ph_variance = 0.5
    
    ph = math.sqrt(ph_variance)* random.random() + ph_mean
    
    if(t%50 < 6):
        return [0]*8

    return [air_temperature,air_moisture,water_depth,soil_moisture,ph,solar_radiation,wind_speed,wind_direction]

#==========================================================================================
#==========================================================================================

if __name__ == '__main__':
    try:
        M5.begin()
        backup = []
        pending = []

        while True:
            pending = backup.copy()
            wlan = connect_to_wifi('Galaxy M21166C', 'nishchay')
            if SERVER == "0.0.0.0":
                SERVER = wlan.ifconfig()[2]
            c = MQTTClient(CLIENT_ID, SERVER)
            c.connect()
            print("Connected to %s" % SERVER)
            c.set_callback(subscribe_callback)
            c.subscribe(SUBSCRIBE_TIME)
            c.subscribe(ACK_CONNECT_PATH)
            c.subscribe(ANOMALY_PATH)
            c.subscribe(IRRIGATION_PATH)
            c.subscribe(STORM_PATH)
            
            # rtc = machine.RTC()
            current_time = machine.RTC().datetime()
            print("RTC time before:", current_time)

            while(is_conn == False):
                print("publishing request")
                c.publish(CONNECT_PATH, f"HIPC {CLIENT_ID.decode()}")
                time.sleep(2)
                c.check_msg() 
                
            current_time = machine.RTC().datetime()
            print("RTC time after:", current_time)

            prev_pub_time = utime.mktime(utime.localtime())
            prev_gen_time = utime.mktime(utime.localtime())
            prev_central_check_time = utime.mktime(utime.localtime())
            v = ""
            
            for k in range(1000):
                
                curr_time = utime.mktime(utime.localtime())
                
                print(curr_time)

                if(curr_time - prev_gen_time > 5):
                    prev_gen_time = curr_time
                    data = getSensorData(k)
                    loc_time = curr_time
                    v = f"{data} :: {loc_time} :: {k}"
                    
                    pending.append(v)
                    backup.append(v)
                    
                    if(len(backup) > 10):
                        backup.pop(0)

                if(curr_time - prev_pub_time > 10):
                    c.check_msg()
                    prev_pub_time = curr_time
                    for each in pending:
                        print("Published %s at %d" % (each, utime.mktime(utime.localtime())))
                        c.publish(DATA_TOPIC, each)
                    pending = []

                if(curr_time - prev_central_check_time > 40):
                    c.check_msg()
                    prev_central_check_time = curr_time
                    if curr_time - last_fetched_time > 30:
                        is_conn=False
                        print("Central device appears inactive, disconnecting")
                        break

                time.sleep(1)
                
            c.disconnect()
            time.sleep(1)
        
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("Unable to import utility module")
    finally:
        c.disconnect()