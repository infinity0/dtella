#!/usr/bin/env python

"""
Dtella - Startup Module
Copyright (C) 2007-2008  Dtella Labs (http://www.dtella.org/)
Copyright (C) 2007-2008  Paul Marks (http://www.pmarks.net/)
Copyright (C) 2007-2008  Jacob Feisley (http://www.feisley.com/)
Copyright (C) 2009  Dtella Cambridge (http://camdc.pcriot.com/)
Copyright (C) 2009  Ximin Luo <xl269@cam.ac.uk>

$Id$

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

# When Dtella is packaged by py2app, dtella.py and the dtella.* package are
# split into separate directories, causing the import to fail.  We'll hack
# around the problem by stripping the base directory from the path.
if __name__ == '__main__':
    try:
        import dtella.common
    except ImportError:
        import sys
        sys.path = [p for p in sys.path if p != sys.path[0]]

# Patch the twisted bugs before doing anything else.
import dtella.common.fix_twisted

import twisted.internet.error
import twisted.python.log
from twisted.internet import reactor
import sys
import socket
import time

try:
    import dtella.build_config as build
except ImportError:
    print 'You need to run "setup.py build" to generate dtella.build_config'

from dtella.common.log import setLogFile
from dtella.common.log import LOG


def addTwistedErrorCatcher(handler):
    def logObserver(eventDict):
        if not eventDict['isError']:
            return
        try:
            text = eventDict['failure'].getTraceback()
        except KeyError:
            text = ' '.join(str(m) for m in eventDict['message'])
        handler(text)
    twisted.python.log.startLoggingWithObserver(logObserver, setStdout=False)


def runBridge(bridge_cfg):
    from dtella.common.util import set_cfg
    set_cfg("dtella.bridge_config", bridge_cfg)

    import dtella.bridge_config as bcfg
    setLogFile(bcfg.cfgname + ".log", 4<<20, 4)
    LOG.debug("Bridge Logging Manager Initialized")

    addTwistedErrorCatcher(LOG.critical)

    from dtella.bridge.main import DtellaMain_Bridge
    dtMain = DtellaMain_Bridge()

    from dtella.bridge.bridge_server import getServiceConfig
    scfg = getServiceConfig()
    scfg.startService(dtMain)

    reactor.run()


def runDconfigPusher(bridge_cfg):
    from dtella.common.util import set_cfg
    set_cfg("dtella.bridge_config", bridge_cfg)

    import dtella.bridge_config as bcfg
    setLogFile(bcfg.cfgname + ".log", 4<<20, 4)
    LOG.debug("Dconfig Pusher Logging Manager Initialized")

    addTwistedErrorCatcher(LOG.critical)

    from dtella.bridge.push_dconfig_main import DtellaMain_DconfigPusher
    dtMain = DtellaMain_DconfigPusher()
    reactor.run()


def terminate(dc_port, killkey):
    # Terminate another Dtella process on the local machine
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', dc_port))
        import dtella.local_config as local
        from base64 import b32encode
        # the extra |$KillDtella| is so we can kill old nodes during an upgrade
        if local.adc_mode:
            sock.sendall("HKILLDTELLA %s\n|$KillDtella|" % b32encode(killkey))
        else:
            sock.sendall("$KillDtella %s|$KillDtella|" % b32encode(killkey))
        print "Sent Packet of Death on port %d..." % dc_port
        sock.shutdown(socket.SHUT_RDWR)
    except socket.error:
        return False
    finally:
        sock.close()

    return True


def runClient(client_cfg, dc_port=None, terminator=False):
    # Set and load the network configuration
    from dtella.common.util import set_cfg
    set_cfg("dtella.local_config", client_cfg)
    import dtella.local_config as local

    # Logging for Dtella Client
    setLogFile(local.cfgname + ".log", 1<<20, 1)
    LOG.debug("Client Logging Manager Initialized")

    if not dc_port:
        import anydbm, dtella.common.state as state
        try:
            sm = state.StateManager(None, local.cfgname, flag='r')
        except anydbm.error:
            sm = state.StateManager(None, local.cfgname, flag='n')

        dc_port = sm.clientport

    # Try to terminate an existing process
    if terminator:
        if terminate(dc_port, sm.killkey):
            # Give the other process time to exit first
            print "Sleeping..."
            time.sleep(2.0)
        else:
            print "Nothing to do."

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Twisted uses these options so we use it too
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', dc_port))
            print "TCP port %s is free." % dc_port
            return 0
        except socket.error, e:
            print "Failed to terminate on port %s: %s." % (dc_port, e)
            return 1
        finally:
            sock.close()

    from dtella.client.main import DtellaMain_Client
    dtMain = DtellaMain_Client()

    from dtella.common.util import get_version_string
    def botErrorReporter(text):
        dch = dtMain.dch
        if dch:
            dch.bot.say(
                "Something bad happened.  You might want to email this to "
                "%s so we'll know about it:\n"
                "Version: %s %s\n%s" %
                (build.bugs_email, local.hub_name, get_version_string()[3:], text))

    addTwistedErrorCatcher(botErrorReporter)
    addTwistedErrorCatcher(LOG.critical)

    if local.adc_mode:
        from dtella.client.adc import ADCFactory
        dfactory = ADCFactory(dtMain, dc_port)
    else:
        from dtella.client.dc import DCFactory
        dfactory = DCFactory(dtMain, dc_port)

    LOG.info("%s-%s on %s" % (build.name, build.version, local.hub_name))

    global exit_code
    exit_code = 0

    def cb(first):
        global exit_code
        try:
            reactor.listenTCP(dc_port, dfactory, interface='127.0.0.1')
        except twisted.internet.error.CannotListenError:
            if first:
                LOG.warning("TCP bind failed.  Killing old process...")
                if terminate(dc_port, dtMain.state.killkey):
                    LOG.info("Ok.  Sleeping...")
                    reactor.callLater(2.0, cb, False)
                else:
                    LOG.error("Kill failed.  Giving up.")
                    reactor.stop()
                    exit_code = 1
            else:
                LOG.error("Bind failed again.  Giving up.")
                reactor.stop()
                exit_code = 1
        else:
            # Kill any old Dtella processes that may be running on a different port
            if dc_port != dtMain.state.clientport:
                terminate(dtMain.state.clientport, dtMain.state.killkey)

            # set a lock
            import hashlib, random
            dtMain.state.killkey = hashlib.sha256(str(random.random())[2:] + \
                str(random.random())[2:] + str(random.random())[2:] + \
                str(random.random())[2:] + str(random.random())[2:] + \
                str(random.random())[2:]).digest()
            dtMain.state.clientport = dc_port

            LOG.info("Listening on 127.0.0.1:%d" % dc_port)
            dtMain.startConnecting()

    reactor.callWhenRunning(cb, True)
    reactor.run()
    return exit_code


def main():
    from optparse import OptionParser, OptionGroup, IndentedHelpFormatter
    parser = OptionParser(
        usage = "Usage: %prog [OPTIONS] [CONFIG]",
        description = "Run Dtella with the given CONFIG. If none is given, the "
                      "user's default one will be used. If the CONFIG to be used "
                      "does not exist, the system default will be copied to its "
                      "location, given by ~/.dtella/${TYPE}_${CONFIG}.cfg",
        version = "%s-%s" % (build.name, build.version),
        formatter = IndentedHelpFormatter(max_help_position=25)
    )

    # custom optgroup class that doesn't indent option group sections
    class MyOptGroup(OptionGroup):
        def format_help(self, formatter):
            formatter.dedent()
            s = OptionGroup.format_help(self, formatter)
            formatter.indent()
            return s

    try:
        import dtella.client
    except ImportError:
        pass
    else:
        group = MyOptGroup(parser, "Client mode options",
            "In this mode, CONFIG should be the name of a network configuration.")
        group.add_option("-p", "--port", type="int",
                         help="listen for the DC client on localhost:PORT", metavar="PORT")
        group.add_option("-t", "--terminate", action="store_true",
                         help="terminate an already-running Dtella client node")
        parser.add_option_group(group)

    try:
        import dtella.bridge
    except ImportError:
        pass
    else:
        group = MyOptGroup(parser, "Bridge mode options",
            "In this mode, CONFIG should be the name of a bridge configuration.")
        group.add_option("-b", "--bridge", action="store_true",
                          help="run as a bridge")
        group.add_option("-d", "--dconfigpusher", action="store_true",
                          help="push seed config data")
        group.add_option("-n", "--network", metavar="CFG",
                          help="when creating a new bridge config, initialise it to use "
                               "the network CFG instead of the default network.")
        group.add_option("-m", "--makeprivatekey", action="store_true",
                          help="make a keypair to use for a new bridge")
        parser.add_option_group(group)

    (opts, args) = parser.parse_args()
    #print opts, args

    config = None
    if len(args) > 0:
        config = args[0]

    # User-specified TCP port
    dc_port = None
    if opts.port:
        try:
            dc_port = opts.port
            if not (1 <= dc_port < 65536):
                raise ValueError
        except ValueError:
            print "Port must be between 1-65535"
            return 2

    try:
        # bridge mode
        if opts.network:
            print "--network has not been implemented yet; you'll have to edit the config yourself"
            return 2

        if opts.bridge:
            return runBridge(config)

        if opts.dconfigpusher:
            return runDconfigPusher(config)

        if opts.makeprivatekey:
            from dtella.bridge.private_key import makePrivateKey
            return makePrivateKey()

    except AttributeError:
        pass

    # client mode
    return runClient(config, dc_port, opts.terminate)


if __name__=='__main__':
    sys.exit(main())

