#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# $Id$
#
# Copyright (c) 2012-2023 "dark[-at-]gotohack.org"
#
# This file is part of pymobiledevice
#
# pymobiledevice is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import plistlib
import ssl
import struct
import logging
import codecs
from re import sub
from six import PY3

from pymobiledevice.usbmux import usbmux

if PY3:
    plistlib.readPlistFromString = plistlib.loads
    plistlib.writePlistToString = plistlib.dumps


class PlistService(object):

    def __init__(self, port, udid=None, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.port = port
        self.connect(udid)

    def connect(self, udid=None):
        mux = usbmux.USBMux()
        mux.process(1.0)
        dev = None

        while not dev and mux.devices :
            mux.process(1.0)
            if udid:
                for d in mux.devices:
                    if d.serial == udid:
                        dev = d
            else:
                dev = mux.devices[0]
                self.logger.info("Connecting to device: " + dev.serial)
        try:
            self.s = mux.connect(dev, self.port)
        except:
            raise Exception("Connexion to device port %d failed" % self.port)
        return dev.serial

    def close(self):
        self.s.close()

    def recv(self, length=4096):
        return self.s.recv(length)

    def send(self, data):
        try:
            self.s.send(data)
        except:
            self.logger.error("Sending data to device failled")
            return -1
        return 0

    def sendRequest(self, data):
        res = None
        if self.sendPlist(data) >= 0:
            res = self.recvPlist()
        return res


    def recv_exact(self, l):
        data = ""
        if PY3:
            data = b""
        while l > 0:
            d = self.recv(l)
            if not d or len(d) == 0:
                break
            data += d
            l -= len(d)
        return data

    def recv_raw(self):
        l = self.recv_exact(4)
        if not l or len(l) != 4:
            return
        l = struct.unpack(">L", l)[0]
        return self.recv_exact(l)

    def send_raw(self, data):
        if PY3 and isinstance(data, str):
            data = codecs.encode(data)
        hdr = struct.pack(">L", len(data))
        msg =  b"".join([hdr,data])
        return self.send(msg)

    def recvPlist(self):
        payload = self.recv_raw()

        if not payload:
            return
        bplist_header = "bplist00"
        xml_header = "<?xml"
        if PY3:
            bplist_header = b"bplist00"
            xml_header = b"<?xml"
        if payload.startswith(bplist_header):
            if PY3:
                result = plistlib.readPlistFromString(payload)
                # print(f"[Andy] plist result1: {result}")
                return result
            else:
                from pymobiledevice.util.bplist import BPlistReader
                return BPlistReader(payload).parse()
        elif payload.startswith(xml_header):
            #HAX lockdown HardwarePlatform with null bytes
            payload = sub('[^\w<>\/ \-_0-9\"\'\\=\.\?\!\+]+','', payload.decode('utf-8')).encode('utf-8')
            result = plistlib.readPlistFromString(payload)
            # print(f"[Andy] plist result2: {result}")
            return result
        else:
            raise Exception("recvPlist invalid data : %s" % payload[:100].encode("hex"))

    def sendPlist(self, d):
        print(f"[Andy] plist params: {d}")

        payload = plistlib.writePlistToString(d)

        # payload to string
        printed_payload = payload.decode('utf-8')
        print(f"[Andy] plist payload: \n {printed_payload}")
        
        l = struct.pack(">L", len(payload))
        return self.send(l + payload)

    def ssl_start(self, keyfile, certfile):
        self.s = ssl.wrap_socket(self.s, keyfile, certfile)
