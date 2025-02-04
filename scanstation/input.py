#!/usr/bin/env python3
# coding=utf-8

import logging
from enum import Enum
from time import sleep
import RPi.GPIO as GPIO


class Input(object):
    wait_time = 0.1
    down = {}


    def event(self, channel):
        self.down[channel] = True


    def pressed(self, button):
        if button.value in self.down and self.down[button.value]:
            self.down[button.value] = False
            return True
        else:
            return False


    def wait(self, timeout=None):
        total = 0
        while not timeout or total < timeout:
           for button in self.Button:
              if self.pressed(button):
                  return button
           sleep(self.wait_time)
           total = total + self.wait_time
        return None


    def __init__(self, buttons):
        self.Button = Enum('Button', buttons, module='input')

        GPIO.setmode(GPIO.BCM)
        for button in self.Button:
            pin = button.value
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin, GPIO.FALLING, callback=self.event, bouncetime=300)
            logging.debug("Button {} connected with GPIO {}".format(button.name, pin))


    def  __del__(self):
       GPIO.cleanup()
       logging.debug("GPIO cleaned up")

