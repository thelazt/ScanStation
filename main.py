#!/usr/bin/env python3
# coding=utf-8

import os
import sys
import logging

from scanstation import ScanStation

logging.basicConfig(level=logging.INFO)

try:
    station = ScanStation('config.ini')

    timeout = 600
    while station.standby(timeout):
        station.action()
        timeout = 60

    station.exit()
except KeyboardInterrupt:
   logging.error('Keyboard interrupt')

