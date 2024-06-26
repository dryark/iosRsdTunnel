# Copyright (c) 2024 Dry Ark LLC <license@dryark.com>
# License AGPL
import asyncio
import logging
import os
import sys
import signal

from ..remote.remoted_tool import stop_remoted, resume_remoted
from ..remote.tunnel_helpers import (
    core_tunnel_service_from_ipv6,
    remote_pair,
    start_tunnel,
)
from ..remote.util import udid_to_rsd_addr
from ..remote.remotexpc import RemoteXPCConnection
from typing import (
    Optional,
    TextIO,
)

try:
    # Proprietary solution
    from cf_mdns import get_remoted_interfaces
except ImportError:
    from ..mdns import get_remoted_interfaces

logger = logging.getLogger(__name__)

async def stop_task():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        # readline returns b"" on EOF (false).  On any other read, it minimally returns b"\n" (true)
        user_input = await reader.readline()
        if not user_input or user_input.decode().lower().strip() == 'stop':
            # Insurance... send ^C to ourselves for whatever else might handle it?
            # Uncomment if we're still getting hung processes later
            # os.kill(os.getpid(), signal.SIGINT)
            break

async def start_tunnel_collector(a,b,c,d):
    async with start_tunnel(
        a,
        secrets=b,
        max_idle_timeout=c,
        protocol=d
    ) as result:
        print(f'{{ "ipv6": "{result.address}", "port": {result.port} }}')
        
        try:
            await stop_task()
        except KeyboardInterrupt:
            pass
        except asyncio.CancelledError:
            print("Exiting")
        
        return result

def stop_loop(loop, task):
    """Stop the event loop and cancel the tasks"""
    print("Stopping loop and cancelling tasks")
    task.cancel()  # Cancel the specific background task
    loop.stop()    # Stop the loop

def run_tunnel(
    service,
    secrets: Optional[TextIO] = None,
    max_idle_timeout: float = 30.0,
    protocol: str = 'quic'
) -> None:
    loop = asyncio.get_event_loop()
    
    tunnel_result = asyncio.run( start_tunnel_collector(
        service,
        secrets,
        max_idle_timeout,
        protocol,
    ) )
    
    #asyncio.run( tunnel_result.client.stop_tunnel() )
    
    logger.info('tunnel was closed')

def remote_tunnel(
    ipv6: Optional[str] = None,
    udid: Optional[str] = None,
) -> None:
    if ipv6 is None and udid is None:
        return
    if ipv6 is not None:
        tunnel_service, udid = core_tunnel_service_from_ipv6( ipv6 = ipv6 )
        logger.debug('device udid:%s',udid)
    else:
        ipv6 = udid_to_rsd_addr( udid, skipResume=True )
        if ipv6 is None:
            print(f'Could not find ipv6 of udid:{udid}')
            return
        logger.debug('device ipv6:%s',ipv6)
        tunnel_service, udid = core_tunnel_service_from_ipv6( ipv6 = ipv6 )
    run_tunnel(
        tunnel_service,
        protocol='quic'
    )

def cli_pair(
    ipv6: Optional[str] = None,
    udid: Optional[str] = None,
) -> None:
    if ipv6 is None and udid is None:
        return
    if udid is not None and ipv6 is None:
        ipv6 = udid_to_rsd_addr( udid, skipResume=True )
        if ipv6 is None:
            print(f'Could not find ipv6 of udid:{udid}')
            return
        logger.debug('device ipv6:%s',ipv6)
    asyncio.run(
        remote_pair( ipv6 = ipv6 )
    )

def cli_list() -> None:
    list_remotes()

RSD_PORT = 58783

def list_remotes() -> None:
    interfaces = get_remoted_interfaces( ios17only = False )
    #print(f'interfaces {interfaces}')
    stop_remoted()
    for iface_info in interfaces:
        interface = iface_info['interface']
        ipv6 = iface_info['ipv6']
        print( f'{{\n  "interface": "{interface}",' )
        print( f'  "ip":"{ipv6}",' )
        service = RemoteXPCConnection((f'{ipv6}%{interface}', RSD_PORT))
        service.connect()
        info = service.receive_response()
        udid = info['Properties']['UniqueDeviceID']
        print(f'  "udid":"{udid}",')
        ios17 = iface_info['hasRemotePairing']
        print(f'  "ios17":{ios17}\n}}')
        service.close()
    resume_remoted()
