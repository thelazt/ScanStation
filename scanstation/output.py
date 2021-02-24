#!/usr/bin/env python3
# coding=utf-8

import logging
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont, Image, ImageDraw


class Output(object):
    def __init__(self, ssd1306address, threshold, rotation):
        serial = i2c(port=1, address=ssd1306address)
        self.image_threshold = threshold
        self.device = ssd1306(serial, rotate=rotation)
        self.background = Image.new(self.device.mode, self.device.size, 'black')
        logging.info("Display mit {}x{} Pixel".format(self.device.width, self.device.height))

    def draw(self):
        draw = ImageDraw.Draw(self.background)
        return draw

    def image(self, img : Image, pos : (int, int)):
        tmp = img.copy()
        tmp.thumbnail(self.device.size)
        self.background.paste(tmp.convert('L').point(lambda x : 255 if x > self.image_threshold else 0, mode='1'), pos)
        del tmp

    def clear(self):
        self.draw().rectangle((0, 0, self.device.width-1, self.device.height-1), outline='black', fill='black')

    def show(self):
        self.device.display(self.background)

