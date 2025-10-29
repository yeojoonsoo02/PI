from gpiozero import Button
import time

SW1 = Button(5, pull_up=False )
SW2 = Button(6, pull_up=False )
SW3 = Button(13, pull_up=False )
SW4 = Button(19, pull_up=False )

oldSw = [0,0,0,0]
newSw = [0,0,0,0]
cnt = [0,0,0,0]

try:
    while True:
        newSw[0] = SW1.is_pressed
        if newSw[0] != oldSw[0]:
            oldSw[0] = newSw[0]
            
            if newSw[0] == 1:
                cnt[0] = cnt[0] + 1
                print("SW1 click",cnt[0])
            
            time.sleep(0.2)
        
        newSw[1] = SW2.is_pressed
        if newSw[1] != oldSw[1]:
            oldSw[1] = newSw[1]
            
            if newSw[1] == 1:
                cnt[1] = cnt[1] + 1
                print("SW2 click",cnt[1])
            
            time.sleep(0.2)
            
        newSw[2] = SW3.is_pressed
        if newSw[2] != oldSw[2]:
            oldSw[2] = newSw[2]
            
            if newSw[2] == 1:
                cnt[2] = cnt[2] + 1
                print("SW3 click",cnt[2])
            
            time.sleep(0.2)
            
        newSw[3] = SW4.is_pressed
        if newSw[3] != oldSw[3]:
            oldSw[3] = newSw[3]
            
            if newSw[3] == 1:
                cnt[3] = cnt[3] + 1
                print("SW4 click",cnt[3])
            
            time.sleep(0.2)

except KeyboardInterrupt:
    pass
