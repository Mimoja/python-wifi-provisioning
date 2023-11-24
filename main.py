#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0

import logging
import threading
import asyncio
import sys
from typing import Any, Dict, Union, Optional

from ble import startBLE
import nmcli

nmcli.disable_use_sudo()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=__name__)


# NOTE: Some systems require different synchronization methods.
trigger: Union[asyncio.Event, threading.Event]
if sys.platform in ["darwin", "win32"]:
    trigger = threading.Event()
else:
    trigger = asyncio.Event()


loop = asyncio.get_event_loop()

logger.info("Starting BLE Provisioning");

# Actually start the server
try:
    loop.run_until_complete(startBLE(loop, trigger))
except KeyboardInterrupt:
    logger.debug("Shutting Down")
    trigger.set()
    pass
