#!/usr/bin/env python3
# coding=utf-8

import os
import sys
import logging
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from enum import Enum
from time import sleep
from configparser import ConfigParser
from PIL import ImageFont, Image


from scanstation.input import Input, Button
from scanstation.output import Output
from scanstation.scanner import Scanner


class ScanStation(object):
    def __init__(self, configfile):
        if not Path(configfile).is_file():
            logging.error('Config file "{}" not found!'.format(configfile))
            sys.exit(1)

        self.config = ConfigParser()
        self.config.read(configfile)

        buttons = {}
        for (key, val) in self.config.items('input'):
            buttons[key.upper()] = int(val)
        self.btn = Input(buttons)

        self.oled = Output(ssd1306address = int(self.config.get('display', 'address', fallback='0x3c'), 16), threshold = self.config.getint('display', 'threshold', fallback=210), rotation = self.config.getint('display', 'rotate', fallback=3))

        self.font = ImageFont.truetype(self.config.get('display', 'font_name'), self.config.getint('display', 'font_size'))
        self.fontSmall = ImageFont.truetype(self.config.get('display', 'font_small_name'), self.config.getint('display', 'font_small_size'))

        self.scanner = Scanner(dev_id = self.config.get('scanner', 'device', fallback=None), source_name = self.config.get('scanner', 'source', fallback=None))
        for (key, val) in self.config.items('scanner'):
            if key != 'device' and key != 'source' and key != 'chunk_size':
                self.scanner.set(key, val)

        if self.config.has_option('process', 'startup'):
            self.display(title = "Starte\nScanStation")
            self.execute(self.config.get('process', 'startup'))

    def execute(self, cmd):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        logging.debug('Run "{}" as PID {}'.format(cmd, process.pid))

        while process.poll() is None:
            while True:
                output = process.stdout.readline().decode()
                if output:
                    logging.debug('PID {}: {}'.format(process.pid, output))
                else:
                    break
        if process.returncode != 0:
            logging.error('Command "{}" (PID {}) failed with exit code {}'.format(cmd, process.pid, process.returncode))
            sys.exit(process.returncode)


    def display(self, title = None, scan = None, footer = None):
        self.oled.clear()

        if scan:
            self.oled.image(scan, (0, 16))

        draw = self.oled.draw()
        if title:
            draw.text((0, 0), text=title, font=self.font, fill="white")

        if footer:
            draw.text((0, 106), text=footer,  font=self.fontSmall, fill="white", align = "center")

        self.oled.show()

    def scanHelper(self, status):
        return self.scanner.scan(abort = lambda: self.btn.pressed(Button.DELETE), status = status, status_refresh = self.config.get('scanner', 'status_refresh', fallback=5), max_page = self.config.get('scanner', 'max_page', fallback=20), chunk_size = self.config.get('scanner', 'chunk_size', fallback=1024 * 1024))

    def scanImages(self, timeout):
        docs = []
        b = Button.NEW
        while b and b != Button.SYNC:
            if b == Button.NEW or (b == Button.ADD and len(docs) == 0):
                pages = self.scanHelper(lambda page, status, img: self.display(title = "Scanne" + status, scan = img, footer = "Seite " + str(1 + page) + "\nDokument " + str(len(docs) + 1)) )
                if pages and len(pages) > 0:
                    docs.append(pages)
                elif len(docs) == 0:
                    return

            elif b == Button.ADD:
                d = len(docs)
                pages = self.scanHelper(lambda page, status, img: self.display(title = "Scanne" + status, scan = img, footer = "Seite " + str(len(docs[d - 1]) + 1 + page) + "\nDokument " + str(d)) )
                if pages and len(pages) > 0:
                    docs[d - 1].extend(pages)

            elif b == Button.DELETE:
                d = len(docs)
                if d == 0 or (d == 1 and len(docs[0]) == 1):
                    del docs[:]
                    return
                if len(docs[d - 1]) == 1:
                    del docs[-1]
                else:
                    del docs[d - 1][-1]

            d = len(docs)
            p = len(docs[d - 1])
            self.display(title = 'Bereit...', scan = docs[d - 1][p - 1], footer = "Seite " + str(p) + "\nDokument " + str(d))

            b = self.btn.wait(timeout)

        return docs

    def generatePDFs(self, docs, prefix):
        pdfs = []

        with tempfile.TemporaryDirectory() as tmpdirname:
            for idx, doc in enumerate(docs):
                self.display(title = "Erstelle\nDokumente", footer = "PDF " + str(idx + 1) + " / " + str(len(docs)))
                pages = []
                for page, scan in enumerate(doc):
                    pages.append(tmpdirname + '/image-' + str(idx) + '-' + str(page)  + '.png')
                    scan.save(pages[-1], format='png')

                files.append(prefix + str(idx) + '.pdf')
                self.execute(self.config.get('process', 'generate').format(images=' '.join(pages), pdf=files[-1]))

        return files

    def importPDFs(self, pdfs):
        for idx, pdf in enumerate(pdfs):
            self.display(title = "PaperWork\nImport...", footer = "PDF " + str(idx + 1) + " / " + str(len(pdfs)))
            self.execute(self.config.get('process', 'import').format(pdf=pdf, index=idx))

    def action(self, timeout = 60):
        with tempfile.TemporaryDirectory() as tmpdirname:
            dt = datetime.now()
            docs = scanImages(timeout)
            pdfs = generatePDFs(docs, tmpdirname + dt.strftime("%Y-%m-%d_%H-%M-%S_"))
            del docs[:]
            if self.config.has_option('process', 'sync'):
                self.display(title = "Sende an\nServer...")
                self.execute(self.config.get('process', 'sync').format(documents=len(docs), date=dt.strftime("%Y-%m-%d"), time=dt.strftime("%H:%M")))

    def standby(self, timeout = 60):
        while True:
            timeout = timeout - 1

            self.display(title='Bereit...', footer = "Schalte in\n" + str(timeout) + " Sek ab")

            b = self.btn.wait(1)
            if b == Button.NEW or b == Button.ADD:
                return True
            elif b == Button.DELETE or timeout <= 0:
                return False

