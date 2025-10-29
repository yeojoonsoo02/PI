from gpiozero import Button
import time

SW1 = Button(5, pull_up=False )
SW2 = Button(6, pull_up=False )
SW3 = Button(13, pull_up=False )
SW4 = Button(19, pull_up=False )

try:
    while True:
        if SW1.is_pressed == True:
            print("go")
        elif SW2.is_pressed == True:
            print("right")
        elif SW3.is_pressed == True:
            print("left")
        elif SW4.is_pressed == True:
            print("back")
        else:
            print("stop")
        
        time.sleep(0.1)
            
except KeyboardInterrupt:
    pass