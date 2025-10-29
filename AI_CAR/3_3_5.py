from gpiozero import  TonalBuzzer,Button
import time

BUZZER = TonalBuzzer(12)
SW1 = Button(5, pull_up=False )
SW2 = Button(6, pull_up=False )
SW3 = Button(13, pull_up=False )
SW4 = Button(19, pull_up=False )

try:
    while True:
        if SW1.is_pressed == True:
            BUZZER.play(261)
        elif SW2.is_pressed == True:
            BUZZER.play(293)
        elif SW3.is_pressed == True:
            BUZZER.play(329)
        elif SW4.is_pressed == True:
            BUZZER.play(349)
        else:
            BUZZER.stop()
            
        
except KeyboardInterrupt:
    pass

BUZZER.stop()