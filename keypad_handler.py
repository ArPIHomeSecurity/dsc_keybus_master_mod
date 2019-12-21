#!/usr/bin/env python
# coding=utf8
'''
Gábor Kovács gkovacs81@gmail.com
'''

import logging
from datetime import datetime
from logging import basicConfig
from multiprocessing import Process
from multiprocessing import Queue
from multiprocessing.queues import Empty
from time import sleep

import RPi.GPIO as GPIO

# Magic numbers
NULL         = 0x00
PLACEHOLDER  = 0xAA
COMMAND_0x81 = 0b10000001
COMMAND_0x01 = 0b00000001
UNKNOWN_DATA  = 0b10010001  # 0x91
PARTITION_DISABLED = 0b11000111  # 0xC7
UNKNOWN_COMMAND = 0xFE
VOID = 0xFF


class Lights:
    BACKLIGHT = 0b10000000 # 0x80
    FIRE      = 0b01000000 # 0x40
    PROGRAM   = 0b00100000 # 0x20
    ERROR     = 0b00010000 # 0x10
    BYPASS    = 0b00001000 # 0x08
    MEMORY    = 0b00000100 # 0x04
    ARMED     = 0b00000010 # 0x02
    READY     = 0b00000001 # 0x01

    def __init__(self):
        self.backlight = True
        self.fire = False
        self.program = False
        self.error = False
        self.bypass = False
        self.memory = False
        self.armed = True
        self.ready = True

    def get_lights(self):
        status = 0
        if self.backlight:
            status |= Lights.BACKLIGHT
        if self.fire:
            status |= Lights.FIRE
        if self.program:
            status |= Lights.PROGRAM
        if self.error:
            status |= Lights.ERROR
        if self.bypass:
            status |= Lights.BYPASS
        if self.memory:
            status |= Lights.MEMORY
        if self.armed:
            status |= Lights.ARMED
        if self.ready:
            status |= Lights.READY
        return status


class Buttons:
    codes = {
        0X00: "0",
        0x05: "1",
        0x0A: "2",
        0x0F: "3",
        0x11: "4",
        0x16: "5",
        0x1B: "6",
        0x1C: "7",
        0x22: "8",
        0x27: "9",
        0x28: "*",
        0x2D: "#",
        0xAF: "Stay",
        0xB1: "Away"
    }

    @staticmethod
    def get_button(value):
        try:
            return Buttons.codes[value]
        except KeyError:
            return f"{value} = ?"


class Line:
    BYTE_GAP = 0.001

    def __init__(self, clock, data):
        self._clock = clock
        self._data = data
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([self._clock, self._data], GPIO.OUT)
        self.conversation = []

    def receive_bit(self):
        GPIO.output(self._clock, 0)
        GPIO.output(self._data, 1)
        sleep(0.000200)
        bit = GPIO.input(self._data)
        sleep(0.000200)
        GPIO.output(self._data, 1)
        GPIO.output(self._clock, 1)
        sleep(0.000450)

        self.conversation.append({"sent_b": 0, "received_b": bit})
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

        self.conversation.append({"sent": byte, "received": int(response, 2)})
        return response

    def send_and_receive(self, messages):
        self.send_receive_byte(messages.pop(0))
        sleep(Line.BYTE_GAP)
        self.receive_bit()
        sleep(Line.BYTE_GAP)

        while messages:
            self.send_receive_byte(messages.pop(0))
            sleep(Line.BYTE_GAP)


class KeypadHandler(Process):
    # COMMANDS
    KEYBUS_QUERY = 0x4C
    PARTITION_STATUS = 0x05
    ZONE_STATUS = 0x27
    ZONE_LIGHTS = 0x0A
    DATETIME_STATUS = 0xA5

    def __init__(self, commands, responses, line):
        super(KeypadHandler, self).__init__()
        self._logger = logging.getLogger("keybus")
        self._commands = commands
        self._responses = responses
        self._lights = Lights()
        self._keypresses = []
        self._line = line

    def run(self):
        try:
            self.communicate()
        except KeyboardInterrupt:
            pass
        except Exception:
            logging.exception("Communication failed!")

    def communicate(self):
        while True:
            try:
                message = self._commands.get(timeout=3)
                self._logger.info("Command: %s", message)

                if message == "SHUTDOWN":
                    break
            except Empty:
                pass

            self._logger.info("Start communication...")
            self.send_command(self.send_partition_status)
            self.send_command(self.send_zone_status)
            self.send_command(self.send_zone_lights)
            self.send_command(self.send_datetime)

    def send_command(self, method):
        method()
        do_keybus_query = self._line.conversation[4]["received"] == self.UNKNOWN_COMMAND

        if self._line.conversation[2]["received"] != VOID:
            message = f"{Buttons.get_button(self._line.conversation[2]['received'])}"
            self._logger.debug("Message: %s", message)
            self._responses.put(message)
        self.print_communication()

        if do_keybus_query:
            self.send_keybus_query()
            self.print_communication()

    def send_keybus_query(self):
        self._logger.info("KEYBUS QUERY 0x%0X" % self.KEYBUS_QUERY)
        self._line.send_and_receive([
            self.KEYBUS_QUERY,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER,
            PLACEHOLDER
        ])

    def send_partition_status(self):
        self._logger.info("PARTITION STATUS 0x%0X" % self.PARTITION_STATUS)
        led_status = self._lights.get_lights()
        self._line.send_and_receive([
            self.PARTITION_STATUS,
            led_status,
            0x01,
            UNKNOWN_DATA,
            PARTITION_DISABLED
        ])

    def send_zone_status(self):
        self._logger.info("ZONE STATUS 0x%0X" % self.ZONE_STATUS)
        led_status = self._lights.get_lights()
        self._line.send_and_receive(self.add_CRC([self.ZONE_STATUS, led_status, 0x01, UNKNOWN_DATA, 0XC7, 0x02]))

    def send_datetime(self):
        timestamp = datetime.now()
        self._logger.info("DATETIME 0x%0X => %s" % (self.DATETIME_STATUS, timestamp.isoformat()))

        b1 = (int((timestamp.year-2000)/10) << 4)
        b1 |= (0x0F & ((timestamp.year-2000) % 10))
        b2 = 0x3C & (timestamp.month << 2)
        b2 |= (timestamp.day & 0b00011000) >> 3
        b3 = (timestamp.day & 0b00000111) << 5
        b3 |= timestamp.hour & 0x1F
        b4 = timestamp.minute << 2
        self._line.send_and_receive(self.add_CRC([self.DATETIME_STATUS, b1, b2, b3, b4, NULL, NULL]))

    def send_zone_lights(self):
        self._logger.info("ZONE LIGHTS 0x%0X" % self.ZONE_LIGHTS)
        led_status = self._lights.get_lights()
        self._line.send_and_receive(self.add_CRC([self.ZONE_LIGHTS, led_status, 0x01, 0x65, NULL, NULL, NULL, NULL]))

    def add_CRC(self, messages):
        total = 0
        for message in messages:
            total += message

        messages.append(total % 256)
        return messages

    def print_communication(self):
        sent = ""
        received = ""
        for message in self._line.conversation:
            if "sent_b" in message and "received_b" in message:
                sent += " {0:01b}".format(message["sent_b"])
                received += " {0:01b}".format(message["received_b"])
            elif "sent" in message and "received" in message:
                sent += " {0:08b}".format(message["sent"])
                received += " {0:08b}".format(message["received"])

        self._logger.info("Sent:     {}".format(sent))
        self._logger.info("Received: {}".format(received))
        try:
            if self._line.conversation[4]["received"] == 0xFE:
                self._logger.info("!!! Unknown command !!!")
        except KeyError:
            pass

        self._line.conversation = []


def main():
    logger = logging.getLogger("main")
    input = Queue()
    output = Queue()
    keypad_handler = KeypadHandler(input, output, Line(clock=5, data=0))
    keypad_handler.start()

    while True:
        try:
            try:
                message = output.get(timeout=1)
                logger.info("Response: %s", message)
            except Empty:
                pass

            if not keypad_handler.is_alive():
                logger.info("Keypad stopped")
                break
        except KeyboardInterrupt:
            logger.info("Exiting...")
            break


if __name__ == "__main__":
    basicConfig(format="%(levelname)6s: %(message)s ", level=logging.INFO)
    main()
