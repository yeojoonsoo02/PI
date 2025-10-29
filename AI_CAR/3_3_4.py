from gpiozero import  TonalBuzzer,Button
import time

BUZZER = TonalBuzzer(12)
SW1 = Button(5, pull_up=False )

oldSw = 0
newSw = 0

try:
    while True:
        newSw = SW1.is_pressed
        if newSw != oldSw:
            oldSw = newSw
            
            if newSw == 1:
                BUZZER.play(391)
                time.sleep(0.2)
                
                BUZZER.stop()
                time.sleep(0.1)
                
                BUZZER.play(391)
                time.sleep(0.2)
                
                BUZZER.stop()
                time.sleep(0.1)
            
            time.sleep(0.2)
        
except KeyboardInterrupt:
    pass

BUZZER.stop()