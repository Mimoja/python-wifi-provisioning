
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0
from typing import Any, Dict, Union, Optional
import sys
import threading
import asyncio
import logging
import json

from improv import *
from bless import (  # type: ignore
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions
)

from wifi import connectToWifi, getCurrentIPs, scanForNetworks
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=__name__)

"""
 Names longer than 10 characters will result in bless
 only advertising the name without the UUIDs on macOS,
 leading to a break with the Improv spec:

 Bluetooth LE Advertisement
The device MUST advertise the Service UUID.
"""
SERVICE_NAME = "Improv"

server = {}

def build_gatt():
    gatt: Dict = {
        ImprovUUID.SERVICE_UUID.value: {
            ImprovUUID.STATUS_UUID.value: {
                "Properties": (GATTCharacteristicProperties.read |
                               GATTCharacteristicProperties.notify),
                "Permissions": (GATTAttributePermissions.readable |
                                GATTAttributePermissions.writeable)
            },
            ImprovUUID.ERROR_UUID.value: {
                "Properties": (GATTCharacteristicProperties.read |
                               GATTCharacteristicProperties.notify),
                "Permissions": (GATTAttributePermissions.readable |
                                GATTAttributePermissions.writeable)
            },
            ImprovUUID.RPC_COMMAND_UUID.value: {
                "Properties": (GATTCharacteristicProperties.read |
                               GATTCharacteristicProperties.write |
                               GATTCharacteristicProperties.write_without_response),
                "Permissions": (GATTAttributePermissions.readable |
                                GATTAttributePermissions.writeable)
            },
            ImprovUUID.RPC_RESULT_UUID.value: {
                "Properties": (GATTCharacteristicProperties.read |
                               GATTCharacteristicProperties.notify),
                "Permissions": (GATTAttributePermissions.readable)
            },
            ImprovUUID.CAPABILITIES_UUID.value: {
                "Properties": (GATTCharacteristicProperties.read),
                "Permissions": (GATTAttributePermissions.readable)
            },
        }
    }
    return gatt


def wifi_connect(ssid: str, passwd: str) -> Optional[list[str]]:
    ssid = ssid.decode('utf-8')
    passwd = passwd.decode('utf-8')
    logger.info(
        f"Connecting to '{ssid}' with password: '{passwd}'")
    if connectToWifi(ssid, passwd):
        allIPs = getCurrentIPs()
        localServer = [f"http://{localIP}" for localIP in allIPs]
        logger.info(
            f"Asking the client to now connect to us under {localServer}")
        return localServer
    return None


def get_wifi_networks() -> Optional[list[str]]:
    ssids = []
    for s in scanForNetworks():
        ssids.append(s.ssid)
    return ssids


improv_server = ImprovProtocol(
    wifi_connect_callback=wifi_connect, wifi_networks_callback=get_wifi_networks, max_response_bytes = 50)


def read_request(
        characteristic: BlessGATTCharacteristic,
        **kwargs
) -> bytearray:
    try:
        improv_char = ImprovUUID(characteristic.uuid)
        logger.info(f"Reading {improv_char} : {characteristic}")
    except Exception:
        logger.info(f"Reading {characteristic.uuid}")
        pass
    if characteristic.service_uuid == ImprovUUID.SERVICE_UUID.value:
        return improv_server.handle_read(characteristic.uuid)
    return characteristic.value


def write_request(
        characteristic: BlessGATTCharacteristic,
        value: bytearray,
        **kwargs
):

    if characteristic.service_uuid == ImprovUUID.SERVICE_UUID.value:
        (target_uuid, target_values) = improv_server.handle_write(
            characteristic.uuid, value)
        if target_uuid != None and target_values != None:
            for value in target_values:
                logging.debug(
                    f"Setting {ImprovUUID(target_uuid)} to {value}")
                server.get_characteristic(
                    target_uuid,
                ).value = value
                success = server.update_value(
                    ImprovUUID.SERVICE_UUID.value,
                    target_uuid
                )
                if not success:
                    logging.warning(
                        f"Updating characteristic return status={success}")


async def startBLE(loop, trigger):
    global server
    server = BlessServer(name=SERVICE_NAME, loop=loop)
    server.read_request_func = read_request
    server.write_request_func = write_request

    await server.add_gatt(build_gatt())
    await server.start()

    logger.info("Server started")

    try:
        trigger.clear()
        if trigger.__module__ == "threading":
            trigger.wait()
        else:
            await trigger.wait()
    except KeyboardInterrupt:
        logger.debug("Shutting Down")
        pass
    await server.stop()
