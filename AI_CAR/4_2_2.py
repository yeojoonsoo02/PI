import serial

bleSerial = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1.0)

try:
    while True:
        data = bleSerial.readline()
        data = data.decode()
        print(data)
        
except KeyboardInterrupt:
    pass

bleSerial.close()