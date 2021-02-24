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

    # Scanner initialisieren...

    while station.standby(timeout):
        station.action()
        timeout = 60

    station.shutdown()
except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
   logging.error('Keyboard interrupt')

