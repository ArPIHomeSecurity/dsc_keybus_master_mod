from gpiozero import LED 
from gpiozero import Button   

#gr = LED(0) 
#ye = LED(5) 
#gr.on() 
#ye.on() 

clock = LED(5)
data = LED(0)

status = [0,0,0,0, 0,1,0,1]

data.on()
clock.on()
from time import sleep 
while True: 
    try: 
        for idx, value in enumerate(status): 
            #data = LED(0)
            clock.on()
            sleep(0.0005)
            clock.off()
            if value: 
                data.on() 
                print("1", end='', flush=True) 
            else: 
                data.off()
                print("0", end='', flush=True) 
            sleep(0.0005)
        print("\nSent")

        clock.on()
        data.on()

        sleep(1)
        continue
        # check keypad response
        data.close()
        data = Button(0)
        sleep(0.0005)
        #clock.off()
        key_response = 0 # data.value
        #print("%s" % key_response)
        #clock.on()

        data.when_pressed = lambda _ : print("PRESSEDDD")
        if not key_response:
            for idx in range(32):
                clock.on()
                sleep(0.0005)
                clock.off()
                print("%d" % data.value, end='', flush=True)
                sleep(0.0005)

        data.close()
        data = LED(0)
        print("")
        sleep(1)


    except KeyboardInterrupt: 
        print("Exit...") 
        break 

