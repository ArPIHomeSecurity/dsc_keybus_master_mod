# coding=utf8

import logging
from logging import basicConfig
from multiprocessing import Process
from queue import Queue, Empty
from time import sleep

import RPi.GPIO as GPIO

COMMAND_0x81 = "10000001"
COMMAND_0x01 = "00000001"
COMMAND_0xC7 = "11000111"
COMMAND_0x91 = "10010001"


def usleep(secs):
    sleep(secs / 1000000)


# LEDs
BACKLIGHT = 0x80
ARMED = 0x02
READY = 0x01


class KeypadHandler(Process):
    _backlight = False
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


            self.send_zone_status()
            self.print_communication()

    def send_byte(self, byte):
        GPIO.output(self._data, 1)
        binary = "{0:08b}".format(byte)
        for bit in binary:
            # self.send_bit(bit)
            GPIO.output(self._clock, 0)
            sleep(0.000200)
            GPIO.output(self._data, int(bit))
            sleep(0.000020)
            GPIO.output(self._clock, 1)
            sleep(0.000020)
            GPIO.output(self._data, 1)
            sleep(0.000100)

        self._communication.append({"sent": byte})

    def receive_bit(self):
        GPIO.output(self._clock, 0)
        GPIO.output(self._data, 1)
        sleep(0.000200)
        bit = GPIO.input(self._data)
        sleep(0.000200)
        GPIO.output(self._data, 1)
        GPIO.output(self._clock, 1)
        sleep(0.000450)
        return bit

    def send_receive_byte(self, byte):
        response = "0b"
        GPIO.output(self._data, 1)
        for bit in "{0:08b}".format(byte):
            GPIO.output(self._clock, 0)
            # GPIO.setup(self._data, GPIO.IN)
            sleep(0.000200)

            response += str(GPIO.input(self._data))
            # sleep(0.000100)
            # GPIO.setup(self._data, GPIO.OUT)
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
        send = [0x05, led_status, 0x01, 0xC7, 0x91]

        self.send_byte(send[0])

        sleep(0.0002)

        response = self.receive_bit()

        # read hack
        keypad_respond = self.receive_bit()
        sleep(0.002)

        self.send_receive_byte(send[1])
        sleep(0.02)
        self.send_receive_byte(send[2])
        sleep(0.02)
        self.send_receive_byte(send[3])
        sleep(0.02)
        self.send_receive_byte(send[4])

        if keypad_respond:
            return response

    def send_zone_status(self):
        print("ZONE STATUS")
        led_status = self.get_led_status()
        send = [0x27, led_status, 0x01, 0xC7, 0x91, 0xFF, 0x6A]

        self.send_byte(send[0])

        sleep(0.0002)

        response = self.receive_bit()

        # read hack
        keypad_respond = self.receive_bit()
        sleep(0.002)

        self.send_receive_byte(send[1])
        # sleep(0.0002)
        self.send_receive_byte(send[2])
        # sleep(0.0002)
        self.send_receive_byte(send[3])
        # sleep(0.0002)
        self.send_receive_byte(send[4])
        self.send_receive_byte(send[5])
        self.send_receive_byte(send[6])

        if keypad_respond:
            return response

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
        for message in self._communication:
            if "sent" in message and "received" in message and message["received"] != 0xFF:
                print("Sent => 0b{0:08b}=0x{0:02x} <= Received {1:08b}=0x{1:02x}".format(message["sent"], message["received"]))
            elif "sent" in message:
                print("Sent => 0b{0:08b}=0x{0:02x}".format(message["sent"]))
            # elif "received" in message:
                # print("Sent => 0b{0:08b}=0x{0:02x} <= Received {1:08b}=0x{1:02x}".format(message["sent"], message["received"]))

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
