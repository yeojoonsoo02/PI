from gpiozero import Button
import time

SW1 = Button(5, pull_up=False )

oldSw = 0
newSw = 0
cnt = 0

try:
    while True:
        newSw = SW1.is_pressed
        if newSw != oldSw:
            oldSw = newSw
            
            if newSw == 1:
                cnt = cnt + 1
                print("click",cnt)
            
            time.sleep(0.2)

except KeyboardInterrupt:
    pass