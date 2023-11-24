#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0

from netaddr import IPNetwork

import os, getopt, sys, json, atexit
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from io import BytesIO

import nmcli
import time

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=__name__)

conname = "meticulousLocalAP"
AP_SSID = "Meticulous Local AP"
AP_PASSWORD = "12345678"

known_wifis = []

def startHotspot():
    return nmcli.device.wifi_hotspot(
        con_name=conname, ssid=AP_SSID, password=AP_PASSWORD)

def stopHotspot():
    for dev in nmcli.device():
        if dev.device_type == 'wifi' and dev.connection == conname:
            logger.info(f"Stopping Hotspot")
            return nmcli.connection.down(conname)


def scanForNetworks(timeout: int = 10, target_network_ssid: str = None):
    global known_wifis
    if target_network_ssid == "":
        target_network_ssid = None
    hotspot_was_stopped = False
    
    for dev in nmcli.device():
        if dev.device_type == 'wifi' and dev.connection == conname:
                stopHotspot()
                hotspot_was_stopped = True
                time.sleep(5)

    target_timeout = time.time() + timeout
    while time.time() < target_timeout:
        logger.info(f"Requesting scan results: Time left: {target_timeout - time.time()}s")
        wifis = []
        try:
            wifis = nmcli.device.wifi()
        except Exception as e:
            logger.info(
                f"Failed to scan for wifis: {e}, retrying if timeout is not reached")
            wifis = []
        for i, w in enumerate(wifis):
            if w.ssid == AP_SSID and w.in_use == True:
                del wifis[i]
                
        if target_network_ssid != None:
            wifis = [w for w in wifis if w.ssid == target_network_ssid]

        if len(wifis) > 0:
            break

    if hotspot_was_stopped and (target_network_ssid == None):
        logger.info("Restarting hotspot")
        startHotspot()
    known_wifis = wifis
    return wifis

def connectToWifi(ssid: str, password: str):
    logger.info(f"Connecting to wifi: {ssid}");
    logger.info(f"Stopping Hotspot for connect")
    try:
        stopHotspot()
    except Exception as e:
        logger.info(f"Failed to stop hotspot: {e}")

    networks = scanForNetworks(timeout=30, target_network_ssid =ssid)
    logger.info(networks)
    if len(networks) > 0:
        logger.info("Target network online, connecting now")
        try:
            nmcli.device.wifi_connect(ssid, password)
        except Exception as e:
            logger.info(f"Failed to connect to wifi: {e}")
            return False

        if len([x for x in networks if x.in_use]) > 0:
            logger.info("Successfully connected");
            return True
    return False


def getCurrentIPs():
    ips = []

    for dev in nmcli.device():
        if dev.device_type == 'wifi' and dev.state == "connected":
            config = nmcli.device.show(dev.device)
            for k,v  in config.items():
                if "IP4.ADDRESS" in k:
                    ip = IPNetwork(v)
                    logger.info(str(ip.ip))
                    ips.append(str(ip.ip))
                if "IP6.ADDRESS" in k:
                    ip = IPNetwork(v)
                    ips.append(str(ip.ip))
    return ips
