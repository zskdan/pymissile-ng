#!/usr/bin/env python
#
#  Written by: Scott Weston <scott@weston.id.au>
#  Edited  by: Zakaria ElQotbi <zakaria@elqotbi.com>
#
# - Version --------------------------------------------------------------
#
#  $Id: missile.py,v 2.0 2011/12/02 15:45:24 scott Exp $
#
# - License --------------------------------------------------------------
#
# Copyright (c) 2006, Scott Weston
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * The name of the contributors may not be used to endorse or promote
#   products derived from this software without specific prior written
#   permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
# OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import usb
import exceptions
import urwid
import urwid.curses_display
import sys
import getopt
import random
import re
import os
from time import sleep, time
from socket import *

vendor_product_ids = [(0x1130,0x0202),(0x0416, 0x9391)]

class centerMissileDevice:
  dev       = None
  handle    = None
  STOP      = 0x0
  LEFT      = 0x8
  RIGHT     = 0x4
  UP        = 0x2
  DOWN      = 0x1
  LEFTUP    = LEFT + UP
  RIGHTUP   = RIGHT + UP
  LEFTDOWN  = LEFT + DOWN
  RIGHTDOWN = RIGHT + DOWN
  FIRE      = 0x10

  def __init__(self,usbdevice):
      try:
        self.handle = usbdevice.open()
        self.handle.reset()
        return
      except NoMissilesError, e:
        raise NoMissilesError()

  def move(self, direction):
     self.handle.controlMsg(0x21, 0x09, [0x5f, direction, 0xe0, 0xff, 0xfe], 0x0300, 0x00)

class legacyMissileDevice:
  dev       = None
  INITA     = (85, 83, 66, 67,  0,  0,  4,  0)
  INITB     = (85, 83, 66, 67,  0, 64,  2,  0)
  CMDFILL   = ( 8,  8,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0,
                0,  0,  0,  0,  0,  0,  0,  0)
  STOP      = ( 0,  0,  0,  0,  0,  0)
  LEFT      = ( 0,  1,  0,  0,  0,  0)
  RIGHT     = ( 0,  0,  1,  0,  0,  0)
  UP        = ( 0,  0,  0,  1,  0,  0)
  DOWN      = ( 0,  0,  0,  0,  1,  0)
  LEFTUP    = ( 0,  1,  0,  1,  0,  0)
  RIGHTUP   = ( 0,  0,  1,  1,  0,  0)
  LEFTDOWN  = ( 0,  1,  0,  0,  1,  0)
  RIGHTDOWN = ( 0,  0,  1,  0,  1,  0)
  FIRE      = ( 0,  0,  0,  0,  0,  1)

  def __init__(self, usbdevice):
    try:
      self.handle = usbdevice.open()
      self.handle.reset()
    except NoMissilesError, e:
      raise NoMissilesError()

  def move(self, direction):
    self.handle.controlMsg(0x21, 0x09, self.INITA, 0x02, 0x01)
    self.handle.controlMsg(0x21, 0x09, self.INITB, 0x02, 0x01)
    self.handle.controlMsg(0x21, 0x09, direction+self.CMDFILL, 0x02, 0x01)

class NoMissilesError(Exception): pass

class UsbDevice:
  def __init__(self):
    busses = usb.busses()
    self.handle = None
    self.launcher = None
    count = 0
    for bus in busses:
      devices = bus.devices
      for dev in devices:
       for i, (vendor_id, product_id) in enumerate(vendor_product_ids):
        if dev.idVendor==vendor_id and dev.idProduct==product_id:
          if count==0:
            self.dev = dev
            self.conf = self.dev.configurations[0]
            self.intf = self.conf.interfaces[0][0]
            self.endpoints = []
            for endpoint in self.intf.endpoints:
              self.endpoints.append(endpoint)
            if i == 0:
              self.launcher = legacyMissileDevice
              return
            elif i == 1:
              self.launcher = centerMissileDevice
              return
          else:
            count=count+1
    raise NoMissilesError()

  def probe(self):
      return self.launcher

  def open(self):
    if self.handle:
      self.handle = None
    self.handle = self.dev.open()
    try:
      self.handle.detachKernelDriver(0)
      self.handle.detachKernelDriver(1)
    except usb.USBError, err:
      print >> sys.stderr, err

    self.handle.setConfiguration(self.conf)
    self.handle.claimInterface(self.intf)
    self.handle.setAltInterface(self.intf)
    return self.handle

class MissileNoDisplay:
  def run(self):
    usbdevice = UsbDevice()
    MissileDevice = usbdevice.probe()
    md = []
    for missiles in range(3):
      try:
        md.append(MissileDevice(usbdevice))
      except NoMissilesError, e:
        break
    if missiles==0:
      raise NoMissilesError
    while 1:
      keys = None
      while not keys:
        keys = raw_input("Enter something: ")
      for k in keys:
        if k == 'window resize':
          size = self.ui.get_cols_rows()
        elif k in ('w', 'up'):
          for m in md:
            m.move(MissileDevice.UP)
        elif k in ('x', 'down'):
          for m in md:
            m.move(MissileDevice.DOWN)
        elif k in ('a', 'left'):
          for m in md:
            m.move(MissileDevice.LEFT)
        elif k in ('d', 'right'):
          for m in md:
            m.move(MissileDevice.RIGHT)
        elif k in ('f', 'space'):
          for m in md:
            m.move(MissileDevice.FIRE)
        elif k in ('s'):
          for m in md:
            m.move(MissileDevice.STOP)
        elif k in ('q'):
          for m in md:
            m.move(MissileDevice.LEFTUP)
        elif k in ('e'):
          for m in md:
            m.move(MissileDevice.RIGHTUP)
        elif k in ('z'):
          for m in md:
            m.move(MissileDevice.LEFTDOWN)
        elif k in ('c'):
          for m in md:
            m.move(MissileDevice.RIGHTDOWN)
        elif k in ('r'):
          for n in range(3):
            for m in md:
              m.move(MissileDevice.FIRE)
              sleep(0.5)
        elif k in ('v'):
          for m in md:
            if  random.random() > 0.8:
              m.move(MissileDevice.FIRE)
        elif k in ('esc'):
          return

class MissileDisplay:
  palette = [ ('body', 'black', 'dark cyan', 'standout'),
              ('footer','light gray', 'dark blue'),
              ('header', 'white', 'dark blue', 'underline'),
              ('important','white', 'dark red', 'bold'),
              ('key', 'light cyan', 'black', 'underline'),
              ('title', 'white', 'black',), ]

  BLANK   = urwid.Text("")
  WARNING = urwid.Text([('important',"CAUTION: AIM AWAY FROM FACE")],
                       align='center')
  HEADER  = urwid.AttrWrap(urwid.Text("MISSILE COMMAND!", align='center'),
                           'header')
  FOOTER  = urwid.AttrWrap(urwid.Text("scott@weston.id.au", align='center'),
                           'footer')
  CONTENT = [ BLANK,
              urwid.Text(["Use the following\n"
                          "keys  to move\n\n"
                          "Q   W   E \n"
                          "  \ | /   \n"
                          "A -(S)- D \n"
                          "  / | \   \n"
                          "Z   X   C \n\n"
                          "F to fire all guns once\n"
                          "R for rapid sequentual fire of all missiles\n"
                          "S to Stop\n"
                          "ESC to Exit\n\n",], align='center'),
              WARNING,
              BLANK, ]

  def __init__(self):
    self.listbox = urwid.ListBox(self.CONTENT)
    view = urwid.AttrWrap(self.listbox, 'body')
    self.view = urwid.Frame(view, header=self.HEADER, footer=self.FOOTER)

  def main(self):
    self.ui = urwid.curses_display.Screen()
    self.ui.register_palette(self.palette)
    self.ui.run_wrapper(self.run)

  def run(self):
    usbdevice = UsbDevice()
    MissileDevice = usbdevice.probe()
    md = []
    for missiles in range(10):
      try:
        md.append(MissileDevice(usbdevice))
      except NoMissilesError, e:
        break
    if missiles==0:
      raise NoMissilesError
    size = self.ui.get_cols_rows()
    while 1:
      canvas = self.view.render(size, focus=1)
      self.ui.draw_screen(size, canvas)
      keys = None
      while not keys:
        keys = self.ui.get_input()
      for k in keys:
        if k == 'window resize':
          size = self.ui.get_cols_rows()
        elif k in ('w', 'up'):
          for m in md:
            m.move(MissileDevice.UP)
        elif k in ('x', 'down'):
          for m in md:
            m.move(MissileDevice.DOWN)
        elif k in ('a', 'left'):
          for m in md:
            m.move(MissileDevice.LEFT)
        elif k in ('d', 'right'):
          for m in md:
            m.move(MissileDevice.RIGHT)
        elif k in ('f', 'space'):
          for m in md:
            m.move(MissileDevice.FIRE)
        elif k in ('s'):
          for m in md:
            m.move(MissileDevice.STOP)
        elif k in ('q'):
          for m in md:
            m.move(MissileDevice.LEFTUP)
        elif k in ('e'):
          for m in md:
            m.move(MissileDevice.RIGHTUP)
        elif k in ('z'):
          for m in md:
            m.move(MissileDevice.LEFTDOWN)
        elif k in ('c'):
          for m in md:
            m.move(MissileDevice.RIGHTDOWN)
        elif k in ('r'):
          for n in range(3):
            for m in md:
              m.move(MissileDevice.FIRE)
              sleep(0.5)
        elif k in ('v'):
          for m in md:
            if  random.random() > 0.8:
              m.move(MissileDevice.FIRE)
        elif k in ('esc'):
          return
        self.view.keypress(size, k)

class MissileNetwork:

  def main(self):
    host = "localhost"
    port = 20000
    buf  = 1024
    addr = (host,port)

    md = []
    lt = 0
    mc = 0
    af = 0
    lpid = 1

    for missiles in range(10):
      try:
        md.append(MissileDevice(missiles))
      except NoMissilesError, e:
        break
    if missiles==0:
      raise NoMissilesError

    UDPSock = socket(AF_INET,SOCK_DGRAM)
    UDPSock.bind(addr)

    while 1:
      cmd,addr = UDPSock.recvfrom(buf)
      cmd = cmd.strip()

      spa = re.split(r':', cmd)
      k = spa[0]
      ppid = spa[1]

      if not k:
        continue
      else:
        if k == "s":
          if ppid != lpid:
            print "Received a STOP for order %s but last order was %s, ignored" % (ppid, lpid)
            continue

        if abs(time()-lt) < 60:
          mc = mc + 1
        else:
          mc = 0
          af = 0
# you can make it noisey here if you wanted to
#         os.system("aplay sounds/firstwarning.wav &")

        if mc > 60 and af == 0:
          k = "v"
# you can make it noisey here if you wanted to
#         os.system("aplay sounds/secondwarning.wav &")

        print "Received via network at %2.2f command %s/%s (move count: %d, %d)" % (time(), k, ppid, mc, af)

        lt = time()
        lpid = ppid

        if k in ('w', 'up'):
          for m in md:
            m.move(MissileDevice.UP)
        elif k in ('x', 'down'):
          for m in md:
            m.move(MissileDevice.DOWN)
        elif k in ('a', 'left'):
          for m in md:
            m.move(MissileDevice.LEFT)
        elif k in ('d', 'right'):
          for m in md:
            m.move(MissileDevice.RIGHT)
        elif k in ('f', 'space'):
          for m in md:
            m.move(MissileDevice.FIRE)
        elif k in ('s', 'S'):
          for m in md:
            m.move(MissileDevice.STOP)
        elif k in ('q'):
          for m in md:
            m.move(MissileDevice.LEFTUP)
        elif k in ('e'):
          for m in md:
            m.move(MissileDevice.RIGHTUP)
        elif k in ('z'):
          for m in md:
            m.move(MissileDevice.LEFTDOWN)
        elif k in ('c'):
          for m in md:
            m.move(MissileDevice.RIGHTDOWN)
        elif k in ('r'):
          for n in range(3):
            for m in md:
              m.move(MissileDevice.FIRE)
              sleep(0.5)
        elif k in ('v'):
          for m in md:
            if random.random() > 0.9:
              m.move(MissileDevice.FIRE)
              af = 1
        elif k in ('esc'):
          UDPSock.close()
          return

def usage():
  print "Usage:"
  print "  -h | --help : this help"
  print "  -n | --network: simple network listener mode (Read the source Luke!)"
  print "  -v | --version: version"
  sys.exit(2)

def version():
  print "$Id: missile.py,v 1.13 2006/07/25 17:01:24 scott Exp $"
  sys.exit(0)

def main(argv):
  try:
    opts, args = getopt.getopt(argv, "hvn", ["help", "version", "network"])
  except getopt.GetoptError:
    print "Sorry, bad option."
    usage()

  if opts:
    for o, a in opts:
      if o in ("-h", "--help"):
        usage()
      elif o in ("-v", "--version"):
        version()
      elif o in ("-n", "--network"):
        try:
          MissileNetwork().main()
        except NoMissilesError, e:
          print "No WMDs found."
          return
      else:
        try:
          MissileDisplay().main()
        except NoMissilesError, e:
          print "No WMDs found."
          return
  else:
    try:
      MissileNoDisplay().run()
    except NoMissilesError, e:
      print "No WMDs found."
      return

if __name__=="__main__":
  main(sys.argv[1:])

