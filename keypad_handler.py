# coding=utf8

import logging
from logging import basicConfig
from multiprocessing import Process
from queue import Queue, Empty
from time import sleep

import RPi.GPIO as GPIO

COMMAND_0x81 = 0b10000001
COMMAND_0x01 = 0b00000001
UNKNOW_DATA = 0b10010001  # 0x91
PARTITION_DISABLED = 0b11000111

PARTITION_STATUS = 0x05
ZONE_STATUS      = 0x27


def usleep(secs):
    sleep(secs / 1000000)


# LEDs
BACKLIGHT = 0b10000000 # 0x80
FIRE      = 0b01000000 # 0x40
PROGRAM   = 0b00100000 # 0x20
ERROR     = 0b00010000 # 0x10
BYPASS    = 0b00001000 # 0x08
MEMORY    = 0b00000100 # 0x04
ARMED     = 0b00000010 # 0x02 
READY     = 0b00000001 # 0x01


class KeypadHandler(Process):
    _backlight = True
    _armed = False
    _ready = True

    def __init__(self, commands, responses):
        super(KeypadHandler, self).__init__()
        self._commands = commands
        self._responses = responses
        GPIO.setmode(GPIO.BCM)
        self._clock = None
        self._data = None
        self._communication = []

    def set_pins(self, clock, data):
        self._clock = clock
        self._data = data
        GPIO.setup([self._clock, self._data], GPIO.OUT)

    def run(self):
        try:
            self.communicate()
        except KeyboardInterrupt:
            pass
        except Exception:
            logging.exception("Communication failed!")

    def communicate(self):
        while True:
            print("Start communication...")
            message = ""
            try:
                message = self._commands.get(timeout=2)
            except Empty:
                pass

            if message == "SHUTDOWN":
                break

            self.send_partition_status()
            self.print_communication()

            # self.send_zone_status()
            # self.print_communication()

    def receive_bit(self):
        GPIO.output(self._clock, 0)
        GPIO.output(self._data, 1)
        sleep(0.000200)
        bit = GPIO.input(self._data)
        sleep(0.000200)
        GPIO.output(self._data, 1)
        GPIO.output(self._clock, 1)
        sleep(0.000450)
        
        self._communication.append({"sent_b": 0, "received_b": bit})
        return bit

    def send_receive_byte(self, byte):
        response = "0b"
        GPIO.output(self._data, 1)
        for bit in "{0:08b}".format(byte):
            GPIO.output(self._clock, 0)
            sleep(0.000200)

            response += str(GPIO.input(self._data))
            GPIO.output(self._data, int(bit))
            sleep(0.000020)
            GPIO.output(self._clock, 1)
            sleep(0.000020)
            GPIO.output(self._data, 1)
            sleep(0.000350)

        self._communication.append({"sent": byte, "received": int(response, 2)})
        return response

    def send_partition_status(self):
        print("PARTITION STATUS")
        led_status = self.get_led_status()
        send = [PARTITION_STATUS, led_status, 0x01, UNKNOW_DATA, PARTITION_DISABLED]

        self.send_receive_byte(send[0])
        sleep(0.001)
        self.receive_bit()
        sleep(0.001)
        self.send_receive_byte(send[1])
        sleep(0.001)
        self.send_receive_byte(send[2])
        sleep(0.001)
        self.send_receive_byte(send[3])
        sleep(0.001)
        self.send_receive_byte(send[4])

    def send_zone_status(self):
        print("ZONE STATUS")
        led_status = self.get_led_status()
        send = [ZONE_STATUS, led_status, 0x01, UNKNOW_DATA, PARTITION_DISABLED, 0x00, 0x01]

        self.send_receive_byte(send[0])
        sleep(0.001)
        self.receive_bit()
        sleep(0.001)
        self.send_receive_byte(send[1])
        sleep(0.001)
        self.send_receive_byte(send[2])
        sleep(0.001)
        self.send_receive_byte(send[3])
        sleep(0.001)
        self.send_receive_byte(send[4])
        sleep(0.001)
        self.send_receive_byte(send[5])
        sleep(0.001)
        self.send_receive_byte(send[6])

    def get_led_status(self):
        status = 0
        if self._backlight:
            status |= BACKLIGHT
        if self._armed:
            status |= ARMED
        if self._ready:
            status |= READY

        return status

    def print_communication(self):
        sent = ""
        received = ""
        for message in self._communication:
            if  "sent_b" in message and "received_b" in message:
                sent += " {0:01b}".format(message["sent_b"])
                received += " {0:01b}".format(message["received_b"])
            elif "sent" in message and "received" in message:
                sent += " {0:08b}".format(message["sent"])
                received += " {0:08b}".format(message["received"])
        
        print("Sent:     {}".format(sent))
        print("Received: {}".format(received))
        self._communication = []

    def print_columns(self):
        for idx, message in enumerate(self._communication):
            if idx in (1, 2):
                print("Sent =>        {0:01b}      <= Received        {1:01b}".format(message["sent"], message["received"]))
            elif "sent" in message and "received" in message and message["received"] != 0xFF:
                print("Sent => {0:08b}=0x{0:02x} <= Received {1:08b}=0x{1:02x}".format(message["sent"], message["received"]))
            elif "sent" in message:
                print("Sent => {0:08b}=0x{0:02x}".format(message["sent"]))

        self._communication = []


def main():

    input = Queue()
    output = Queue()
    keypad_handler = KeypadHandler(input, output)
    keypad_handler.set_pins(5, 0)
    keypad_handler.start()

    while True:
        try:
            if not keypad_handler.is_alive():
                print("Keypad stopped")
                break
            sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")
            break


if __name__ == "__main__":
    basicConfig(format="%(levelname)6s: %(message)s ", level=logging.DEBUG)
    main()
