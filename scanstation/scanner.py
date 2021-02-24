#!/usr/bin/env python3
# coding=utf-8

import logging
from datetime import datetime
from PIL import Image
import gi
gi.require_version('Libinsane', '1.0')
from gi.repository import GObject  # noqa: E402
from gi.repository import Libinsane  # noqa: E402

class Scanner(object):
    dev = None

    class Logger(GObject.GObject, Libinsane.Logger):
        logging = None

        def do_log(self, lvl, msg):
            if not self.logging:
                self.logging = logging.getLogger("Libinsane")
            if lvl == Libinsane.LogLevel.DEBUG:
                self.logging.debug(msg)
            elif lvl == Libinsane.LogLevel.INFO:
                self.logging.info(msg)
            elif lvl == Libinsane.LogLevel.WARNING:
                self.logging.warning(msg)
            elif lvl == Libinsane.LogLevel.ERROR:
                self.logging.error(msg)


    def __init__(self, dev_id : str = None, source_name : str = None):
        self.libinsanelogger = self.Logger()
        Libinsane.register_logger(self.libinsanelogger)

        # scan device
        api = Libinsane.Api.new_safebet()
        if dev_id is None:
            devs = api.list_devices(Libinsane.DeviceLocations.ANY)
            if len(devs) == 0:
                raise Exception("No scan device find!")
            dev_id = devs[0].get_dev_id()
        self.dev = api.get_device(dev_id)
        logging.info("Using {} ({})".format(dev_id, self.dev.get_name()))

        # scan source
        sources = self.dev.get_children()
        for src in sources:
            if src.get_name() == source_name:
                self.source = src
                break
        else:
            if source_name is None:
                self.source = sources[0] if len(sources) > 0 else dev
            elif source_name == 'root':
                self.source = self.dev
            else:
                raise Exception("Source '{}' not found".format(source_name))
        logging.info("Using use scan source {}".format(self.source.get_name()))

        self.opts = {opt.get_name(): opt for opt in self.source.get_options()}

    def __del__(self):
        if self.dev:
            self.dev.close()


    def set(self, name : str, value):
        if name in self.opts:
            old = self.opts[name].get_value()
            if old != value:
                logging.info("Setting scanner option {} from {} to {}".format(name, old, value))
                self.opts[name].set_value(value)
            else:
                logging.info("Scanner option {} is already set to {}".format(name, value))
        
    def bytes2img(self, params, bytes) -> Image:
        fmt = params.get_format()
        assert(fmt == Libinsane.ImgFormat.RAW_RGB_24)
        (w, h) = (
            params.get_width(),
            int(len(bytes) / 3 / params.get_width())
        )
        return Image.frombuffer("RGB", (w, h), bytes, "raw", "RGB", 0, 1).convert('L')


    def scan(self, abort = None, status = None, status_refresh : int = 5, max_page : int = 20, chunk_size = 1024 * 1024):
        session = self.source.scan_start()
        pages = []
        try:
            while not session.end_of_feed() and len(pages) < max_page:
                logging.info("Scanning new page {}".format(len(pages) + 1))
                if status:
                    status(len(pages), '...', None)
                last_refresh = datetime.now()

                params = session.get_scan_parameters()
                total = params.get_image_size()
                bytes = []
                r = 0

                while not session.end_of_page():
                    data = session.read_bytes(chunk_size).get_data()
                    bytes.append(data)
                    r += len(data)

                    refresh_delta = datetime.now() - last_refresh
                    if abort and abort():
                        logging.info("Scan aborted")
                        session.cancel()
                        return None
                    elif status and refresh_delta.seconds >= status_refresh:
                        img = self.bytes2img(params, b"".join(bytes))
                        status(len(pages), " " + str(int(r * 100 / total)) + "%", img)
                        del img
                        last_refresh = datetime.now()

                logging.info("Scan of page {} finished".format(len(pages) + 1))
                img = self.bytes2img(params, b"".join(bytes))
                pages.append(img)
                del img
        except BaseException as error:
            logging.error(error)
        finally:
            session.cancel()
        return pages

