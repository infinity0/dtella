"""
Dtella - AdvancedDirectConnect Interface Module
Copyright (C) 2008  Dtella Labs (http://www.dtella.org)
Copyright (C) 2008  Paul Marks
Copyright (C) 2009  Dtella Cambridge (http://camdc.pcriot.com/)
Copyright (C) 2009  Andrew Cooper <amc96>, Ximin Luo <xl269> (@cam.ac.uk)

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

from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet.protocol import ServerFactory, ClientFactory
from twisted.internet import reactor
from twisted.python.runtime import seconds
import twisted.python.log

from dtella.common.util import (validateNick, word_wrap, split_info,
                                split_tag, dc_escape, dc_unescape,
                                dcall_discard, format_bytes, dcall_timeleft,
                                get_version_string, lock2key, CHECK, b32pad,
                                adc_escape, adc_unescape, adc_locdes,
                                adc_infostring, adc_infodict)
from dtella.client.dtellabot import DtellaBot
from dtella.common.ipv4 import Ad
import dtella.common.core as core
import dtella.local_config as local
import struct
import random
import re
import binascii
import socket
from tiger import hash, treehash
from base64 import b32encode, b32decode

from zope.interface import implements
from zope.interface.verify import verifyClass
from dtella.common.interfaces import IDtellaStateObserver



# Login Procedure
# H<C HSUP ADBASE ADTIGR ...
# H>C ISUP ADBASE ADTIGR ...
# H>C ISID <client-sid>
# H>C IINF HU1 HI1
# H<C BINF <my-sid> ID... PD...
#(
# H>C IGPA ...
# H<C HPAS ...
#)
# H>C BINF <all clients>
# H>C BINF <Client-SID>
# ...


class BaseADCProtocol(LineOnlyReceiver):
    '''
    BaseADCProtocol is a subclass of LineOnlyReciever

    It is the class responsible for communicating with the DC client
    and implements the basic decoding logic for incoming lines
    '''

    delimiter='\n'

    def connectionMade(self):
        try:
            self.transport.setTcpNoDelay(True)
        except socket.error:
            pass
        self.dispatch = {}


    def sendLine(self, line):
        #print "<:", line
        LineOnlyReceiver.sendLine(self, line)


    def lineReceived(self, line):

        if(len(line) == 0):
            self.sendLine('') # Keepalive
            return

        #print ">:", line
        cmd = line.split(' ', 1)
        args = {}
        args['con'] = cmd[0][0]
        msg = cmd[0][1:]

        if args['con'] == 'E': # If its an echo context, echo it back
            self.sendLine(line)

        #print "Context: %s Message: %s" % (args['con'],msg)

        # Do a dict lookup to find the parameters for this command
        try:
            contexts, fn = self.dispatch[msg]
        except KeyError:
            print "Error: Unknown command \"%s\"" % line
            return

        if contexts is None:
            fn(line)
        elif(args['con'] not in contexts):
            print "Invalid context %s for command %s" % (args['con'], cmd)
            return

        try:
            if args['con'] in ('B', 'F'):
                args['src_sid'], args['rest'] = cmd[1].split(' ',1)
                fn(**args)
            elif args['con'] in ('C', 'I', 'H'):
                args['rest'] = cmd[1]
                fn(**args)
            elif args['con'] in ('D', 'E'):
                args['src_sid'], args['dst_sid'], args['rest'] = cmd[1].split(' ',2)
                fn(**args)
            else:
                raise
        except:
            twisted.python.log.err()



    def addDispatch(self, command, contexts, fn):
        self.dispatch[command] = (contexts, fn)


##############################################################################

# These next 3 classes implement a small subset of the DC client-client
# protocol, in order to impersonate a remote peer and generate an error.

class ADC_AbortTransfer_Factory(ClientFactory):

    def __init__(self, cid, token, reason):
        self.cid = cid
        self.token = token
        self.reason = reason

    def buildProtocol(self, addr):
        p = ADC_AbortTransfer_Out(self.cid, self.token, self.reason)
        p.factory = self
        return p


class ADC_AbortTransfer_Out(BaseADCProtocol):

    # if I initiate the connection:
    # send CSUP
    # (catch CSUP followed by CINF)
    # send CINF
    # (catch GFI or GET then abort connection)

    def __init__(self, cid, token, reason):

        self.cid = cid
        self.token = token
        self.reason = reason

        # If we're not done in 5 seconds, something's fishy.
        def cb():
            self.timeout_dcall = None
            self.transport.loseConnection()

        self.timeout_dcall = reactor.callLater(5.0, cb)


    def connectionMade(self):
        BaseADCProtocol.connectionMade(self)

        self.addDispatch('SUP', ('C'), self.d_SUP)
        self.addDispatch('INF', ('C'), self.d_INF)

        self.sendLine("CSUP ADBASE ADTIGR")


    def d_SUP(self, con, rest=None):
        pass # We will recieve one but ignore it

    def d_INF(self, con, rest=None):

        self.addDispatch('GET', ('C'), self.d_GET)
        self.addDispatch('GFI', ('C'), self.d_GFI)

        self.sendLine("CINF ID%s TO%s" % (self.cid, self.token))


    def d_GET(self, con, rest=None):
        self.sendLine("CSTA 151 %s" % adc_escape(self.reason))
        self.transport.loseConnection()

    def d_GFI(self, con, rest=None):
        self.sendLine("CSTA 151 %s" % adc_escape(self.reason))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        dcall_discard(self, 'timeout_dcall')


class ADC_AbortTransfer_In(BaseADCProtocol):

    # if I receive the connection:
    # receive $MyNick
    # wait for $Lock
    # -> send $MyNick + $Lock + $Supports + $Direction + $Key
    # wait for $Key
    # -> send $Error

    def __init__(self, cid, token, dch, reason=None):

        self.cid = cid
        self.token = token
        self.reason = reason

        # Steal connection from the DCHandler
        self.factory = dch.factory
        self.makeConnection(dch.transport)
        self.transport.protocol = self

        # Steal the rest of the data
        self._buffer = dch._buffer
        dch.lineReceived = self.lineReceived


        # If we're not done in 5 seconds, something's fishy.
        def cb():
            self.timeout_dcall = None
            self.transport.loseConnection()

        self.timeout_dcall = reactor.callLater(5.0, cb)


    def connectionMade(self):
        BaseADCProtocol.connectionMade(self)

        self.addDispatch('INF', ('C'), self.d_INF)
        self.addDispatch('STA', ('C'), self.d_STA)
        self.addDispatch('GET', ('C'), self.d_GET)
        self.addDispatch('GFI', ('C'), self.d_GFI)

        self.sendLine("CSUP ADBASE ADTIGR")

    def d_STA(self, con, rest):
        pass

    def d_INF(self, con, rest):
        self.sendLine("CINF ID%s" % self.cid)

    def d_GET(self, con, rest):
        self.sendLine("CSTA 151 %s" % adc_escape(self.reason))
        self.transport.loseConnection()

    def d_GFI(self, con, rest):
        self.sendLine("CSTA 151 %s" % adc_escape(self.reason))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        dcall_discard(self, 'timeout_dcall')




##############################################################################


class ADCHandler(BaseADCProtocol):
    implements(IDtellaStateObserver)

    def __init__(self, main):
        self.main = main
        self.info = ''
        self.infdict = {}
        self.nick = ''
        self.locstr = ''
        self.sid = core.NickManager.baseSID

    def initDataReceived(self, data):
        """Attempt to detect incoming clients not using ADC."""
        #print ">>:", data
        dcall_discard(self, 'init_dcall')

        if data[0] == '$':
            from dtella.client.dc import AbortConnection
            AbortConnection(self, data, "ADC", "adc://localhost:%s" %
                self.main.state.clientport)
        else:
            # Passed all tests, let it through
            self.dataReceived = self._dataReceived
            self.dataReceived(data)


    def connectionMade(self):
        BaseADCProtocol.connectionMade(self)

        self.bot = DtellaBot(self, '*Dtella')
        self.bot.sid = b32encode(treehash(chr(1)))[:4]
        self.bot.cid = b32encode(treehash(self.bot.nick))
        self.bot.dcinfo = "ID%s I4127.0.0.1 SS0 SF0 VE%s US0 DS0 SL0 AS0 AM0 NI%s DE%s HN1 HR1 HO1 CT31" % \
                        (self.bot.cid,get_version_string(), self.bot.nick,
                        "Local\\sDtella\\sBot")

        # Handlers which can be used before attaching to Dtella
        self.addDispatch('KILLDTELLA',     ('H'), self.d_KillDtella)
        self.addDispatch('SUP',             ('H','C'),self.d_SUP)
        self.addDispatch('INF',             ('B'),self.d_INF)

        # Chat messages waiting to be sent
        self.chatq = []
        self.chat_counter = 99999
        self.chatRate_dcall = None

        # ['PROTOCOL', 'IDENTIFY', 'queued', 'ready', 'invisible']
        self.state = 'PROTOCOL'

        self.queued_dcall = None
        self.autoRejoin_dcall = None

        self.scheduleChatRateControl()

        # Set up the protocol trap
        self._dataReceived = self.dataReceived
        self.dataReceived = self.initDataReceived

        # If we receive no data for 1 second, send a DC hubstring in case
        # it's a DC client, so we can gracefully abort the connection attempt.
        # (ADC clients seem to ignore this even if they receive it.)
        def cb():
            self.init_dcall = None
            if self.state == 'PROTOCOL':
                self.transport.writeSequence(("$Lock FOO Pk=BAR", '|'))
                self.transport.writeSequence(("$HubName %s" % local.hub_name, '|'))

        self.init_dcall = reactor.callLater(1.0, cb)



    def isOnline(self):
        osm = self.main.osm
        return (self.state == 'ready' and osm and osm.syncd)


    def connectionLost(self, reason):

        self.main.removeDCHandler(self)

        dcall_discard(self, 'init_dcall')
        dcall_discard(self, 'chatRate_dcall')
        dcall_discard(self, 'autoRejoin_dcall')


    def fatalError(self, text):
        self.pushStatus("ERROR: %s" % text)
        self.transport.loseConnection()


    def checkForceCrypto(self, protocol):
        return local.adc_mode and local.adc_fcrypto and \
            'ADC0' not in protocol and 'ADCS' not in protocol


    def d_KillDtella(self, con, rest):
        k = self.main.state.killkey
        if b32encode(k) == rest:
            self.sendLine("IKILLDTELLA 0 OK")
            def cb():
                reactor.stop()
            reactor.callLater(0, cb)
        else:
            self.sendLine("IKILLDTELLA 1 BADKEY")


    def d_SUP(self, con, rest=None):
        features = rest.split(' ')
        if 'ADBASE' not in features or 'ADTIGR' not in features:
            print "Client doesn't support ADC/1.0"
            self.transport.loseConnection()
            return

        if con == 'C':  # Fake RCM reply
            ADC_AbortTransfer_In(ADCHandler.fake_cid, ADCHandler.fake_token, self, ADCHandler.fake_reason)

        elif self.state == 'PROTOCOL':
            self.sendLine("ISUP ADBASE ADTIGR")
            self.sendLine("ISID %s" % self.sid)
            self.sendLine("IINF CT32 NI%s" % adc_escape(local.hub_name))
            self.state = 'IDENTIFY'

        else:
            print "Error in %sSUP - rest: %s" % (con, rest)


    def d_INF(self, con, src_sid=None, rest=None):

        inf = adc_infodict(rest)

        if self.state == 'IDENTIFY':
            inf['PD'] = b32pad(inf['PD'])
            inf['ID'] = b32pad(inf['ID'])

            if b32encode(hash(b32decode(inf['PD']))) != inf['ID']:
                self.sendLine("ISTA 227 Invalid\\sPID");
                self.transport.loseConnection()
                return
            del inf['PD']

            # Let Dtella logon so we can send messages to the user
            self.sendLine("BINF %s %s" % (self.bot.sid, self.bot.dcinfo))

            # From ValidateNick
            reason = validateNick(inf['NI'])

            if reason:
                self.pushStatus("Your nick is invalid: %s" % reason)
                self.pushStatus("Please fix it and reconnect.  Goodbye.")
                self.sendLine("ISTA 221 Invalid\\sNick")
                self.transport.loseConnection()
                return

            self.nick = inf['NI']

            # update MeNode
            self.infdict.update(inf)
            self.infstr = self.formatMyInfo(True)
            if self.main.osm:
                self.main.osm.me.info = self.infdict
                self.main.osm.me.dcinfo = self.infstr
            self.sendLine("BINF %s %s" % (src_sid, self.infstr))

            if 'SU' in inf and ('ADC0' in inf['SU'] or 'ADCS' in inf['SU']):
                self.crypto = True
            else:
                self.crypto = False

            # detect non-encryption
            if local.adc_mode and local.adc_fcrypto and not self.crypto:
                text = (
                    "="*80,
                    "This network requires all client-client connections to "
                    "be encrypted. You will be unable to connect to other "
                    "people until you reconnect with TLS support. For most "
                    "clients, you will have to do two things: ",
                    "",
                    "(1) Set a TLS port:",
                    "    - Set a port between 10000 and 65336, or blank/0 for "
                    "random.",
                    "    - This port needs to be *different* from the normal "
                    "TCP port setting. (TLS is just encrypted TCP.)",
                    "    - If you have a firewall/router, you may need to "
                    "allow incoming connections to your DC client, or the "
                    "specified ports.",
                    "(2) TLS settings:",
                    "    - Enable \"Use TLS connections to clients without "
                    "trusted certificates\"",
                    "    - Enable \"Use TLS connections to hubs without "
                    "trusted certificates\"",
                    "    - Enable \"Use TLS when remote client supports it\"",
                    "",
                    "The settings can be found:",
                    "",
                    " - StrongDC++/DC++:",
                    "    (1) Set a TLS port: File / Settings / Connection "
                    "Settings",
                    "    (2) TLS settings: File / Settings / Security",
                    " - linuxdcpp:",
                    "    (1) Set a TLS port: File / Preferences / Connection",
                    "    (2) TLS settings: File / Preferences / Advanced / "
                    "Security Certificates",
                    "",
                    "You have to restart your client for any security setting "
                    "changes to take effect.",
                    "",
                    "As of 2009-04-20, most other clients do NOT support "
                    "encryption; these will be unable to connect.",
                    "="*80,
                    )

                for par in text:
                    for line in word_wrap(par):
                        self.pushBotMsg(line)

            # detect passive
            if 'I4' not in inf:
                text = (
                    "="*80,
                    "You are currently in passive mode. This is less helpful "
                    "to the network, because passive mode users can't connect "
                    "to other passive mode users.",
                    "",
                    "Since your router/firewall (if you have one) is allowing "
                    "your connection to the Dtella network, it is likely that "
                    "active mode DC will work fine too, so please try to use "
                    "it. For most clients, this will involve something along "
                    "the lines of:",
                    "",
                    "File: Settings/Preferences: Connection: Incoming: "
                    "select \"Active mode\" or \"Direct connection\"",
                    "",
                    "You have to reconnect to Dtella for any connection mode "
                    "setting changes to take effect.",
                    "",
                    "To test whether active mode works, just try to get "
                    "someone's file list. If it doesn't seem to work, please "
                    "try to exhaust all possibilites (eg. check your firewall "
                    "settings, etc) before resorting to passive mode. Feel "
                    "free to ask for help in the main chat channel.",
                    "="*80,
                    )

                for par in text:
                    for line in word_wrap(par):
                        self.pushBotMsg(line)

            # login procedue - replaced from removeLoginBlockers
            if self.main.dch is None:
                self.attachMeToDtella()

            elif self.main.pending_dch is None:
                self.state = 'queued'
                self.main.pending_dch = self

                def cb():
                    self.queued_dcall = None
                    self.main.pending_dch = None
                    self.pushStatus("Nope, it didn't leave.  Goodbye.")
                    self.transport.loseConnection()

                self.pushStatus(
                    "Another DC client is already using Dtella on this computer.")
                self.pushStatus(
                    "Waiting 5 seconds for it to leave.")

                self.queued_dcall = reactor.callLater(5.0, cb)

            else:
                self.pushStatus(
                    "Dtella is busy with other DC connections from your "
                    "computer.  Goodbye.")
                self.transport.loseConnection()

            self.state = 'ready'

        elif self.state == 'ready':
            # update MeNode
            self.infdict.update(inf)
            self.infstr = self.formatMyInfo(True)
            if self.main.osm:
                self.main.osm.me.info = self.infdict
                self.main.osm.me.dcinfo = self.infstr
            self.sendLine("BINF %s %s" % (src_sid, self.infstr))


    def d_MSG(self, con, src_sid=None, dst_sid=None, rest=None):

        if not rest:
            return

        params = rest.split(' ')
        text = adc_unescape(params[0])

        inf = {}
        if len(params)>1:
            for i in params[1:]:
                inf[i[:2]] = i[2:]

        if con == 'E':  # Private Message

            if dst_sid == self.bot.sid:

                # No ! is needed for commands in the private message context
                if text[:1] == '!':
                    text = text[1:]

                def out(text):
                    if text is not None:
                        self.bot.say(text)

                self.bot.commandInput(out, text)
                return

            if len(text) > 10:
                shorttext = text[:10] + '...'
            else:
                shorttext = text

            def fail_cb(detail):
                self.pushPrivMsg(
                    nick,
                    "*** Your message \"%s\" could not be sent: %s"
                    % (shorttext, detail))

            if not self.isOnline():
                fail_cb("You're not online.")
                return

            try:
                n = self.main.osm.nkm.lookupNodeFromSID(dst_sid)
            except KeyError:
                fail_cb("User doesn't seem to exist.")
                return

            n.event_PrivateMessage(self.main, text, fail_cb )

        else:           # Public message

            # Route commands to the bot
            if text[:1] == '!':

                def out(out_text, flag=[True]):

                    # If the bot produces output, inject our text input before
                    # the first line.
                    if flag[0]:
                        self.pushChatMessageBySID(self.bot.sid, "You commanded: %s" % text)
                        flag[0] = False

                    if out_text is not None:
                        self.pushChatMessageBySID(self.bot.sid, out_text)

                if self.bot.commandInput(out, text[1:], '!'):
                    return

            if not self.isOnline():
                self.pushStatus("*** You must be online to chat!")
                return

            if self.main.osm.isModerated():
                self.pushStatus(
                    "*** Can't send text; the chat is currently moderated.")
                return

            text = text.replace('\r\n','\n').replace('\r','\n')

            for line in text.split('\n'):

                # Skip empty lines
                if not line:
                    continue

                # Limit length
                if len(line) > 1024:
                    line = line[:1024-12] + ' [Truncated]'

                flags = 0

                # Check for ME1 flag (ADC specific)
                try:
                    if inf['ME'] == '1':
                        flags |= core.SLASHME_BIT
                except KeyError:
                    pass

                # Check for /me incase the client misses it
                if len(line) > 4 and line[:4].lower() in ('/me ','+me ','!me '):
                    line = line[4:]
                    flags |= core.SLASHME_BIT

                # Check rate limiting
                if self.chat_counter > 0:

                    # Send now
                    self.chat_counter -= 1
                    self.broadcastChatMessage(flags, line)

                else:
                    # Put in a queue
                    if len(self.chatq) < 5:
                        self.chatq.append( (flags, line) )
                    else:
                        self.pushStatus(
                            "*** Chat throttled.  Stop typing so much!")
                        break


    def d_CTM(self, con, src_sid, dst_sid, rest):
        show_errors = True
        node = None

        try:
            protocol_str, port_str, token = rest.split(' ')
        except Exception:
            print "CTM Error: rest=%s" % rest
            return

        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            port = None

        def fail_cb(reason, bot = False):
            if show_errors:
                if node:
                    self.pushStatus("*** Connection to <%s> failed: %s" % (node.nick, reason))
                else:
                    self.pushStatus("*** Connection failed: %s" % reason)
            if port:
                if bot:
                    reactor.connectTCP('127.0.0.1', port,
                        ADC_AbortTransfer_Factory(self.bot.cid, token, reason))
                else:
                    reactor.connectTCP('127.0.0.1', port,
                        ADC_AbortTransfer_Factory(node.info['ID'], token, reason))

        if not self.isOnline():
            fail_cb("You are not online.")
            return
        elif not port:
            fail_cb("Invalid port: <%s>" % port_str)
            return
        elif self.isLeech():
            show_errors = False
            fail_cb(None)
            return

        try:
            node = self.main.osm.nkm.lookupNodeFromSID(dst_sid)
        except KeyError:
            node = None
            if dst_sid == self.bot.sid:
                fail_cb("<%s> has no files" % self.bot.nick,True)
            else:
                fail_cb("User doesnt seem to exist")
            return

        if node.protocol != self.protocol:
            fail_cb("Remote user is not using the ADC Protocol")
        elif node.is_peer and self.checkForceCrypto(protocol_str):
            if self.crypto:
                fail_cb("Remote user is not using encrypted connections")
            else:
                fail_cb("You are not using encrypted connections")
        else:
            node.event_ADC_ConnectToMe(self.main, protocol_str, port, token, fail_cb)


    def d_RCM(self, con, src_sid, dst_sid, rest):
        show_errors = True
        cancel = True

        # Older clients dont send a token as part of RCM
        # This is caused by a bug in the v0.698 DC core
        try:
            protocol_str, token = rest.split(' ')
        except Exception:
            return

        def fail_cb(reason, bot = False):
            if show_errors:
                if node:
                    self.pushStatus("*** Connection to <%s> failed: %s" % (node.nick, reason))
                else:
                    self.pushStatus("*** Connection failed: %s" % reason)

            if bot:
                ADCHandler.fake_cid = self.bot.cid
                ADCHandler.fake_token = token
                ADCHandler.fake_reason = reason
                self.sendLine("DCTM %s %s %s %s %s"% (dst_sid, src_sid, protocol_str, self.factory.listen_port, token))
            else:
                old_i4 = node.info['I4']
                ADCHandler.fake_cid = node.info['ID']
                ADCHandler.fake_token = token
                ADCHandler.fake_reason = reason
                self.sendLine("BINF %s I4127.0.0.1" % dst_sid)
                self.sendLine("DCTM %s %s %s %s %s"% (dst_sid, src_sid, protocol_str, self.factory.listen_port, token))
                self.sendLine("BINF %s I4%s" % (dst_sid, old_i4))

        if not self.isOnline():
            fail_cb("You are not online.")
            return
        elif self.isLeech():
            show_errors = False
            fail_cb(None)
            return

        try:
            node = self.main.osm.nkm.lookupNodeFromSID(dst_sid)
        except KeyError:
            node = None
            if dst_sid == self.bot.sid:
                fail_cb("<%s> has no files" % self.bot.nick,True)
            else:
                fail_cb("User doesnt seem to exist")
            return

        if node.protocol != self.protocol:
            fail_cb("Remote user is not using the ADC Protocol")
        elif node.is_peer and self.checkForceCrypto(protocol_str):
            if self.crypto:
                fail_cb("Remote user is not using encrypted connections")
            else:
                fail_cb("You are not using encrypted connections")
        else:
            node.event_ADC_RevConnectToMe(self.main, protocol_str, token, fail_cb)


    def d_SCH(self, con, src_sid, rest):
        # Search request

        if not self.isOnline():
            self.pushStatus("Can't Search: Not online!")
            return

        if len(rest) > 65535:
            self.pushStatus("Search string too long")
            return

        osm = self.main.osm

        packet = osm.mrm.broadcastHeader('AQ', osm.me.ipp)
        packet.append(struct.pack('!I', osm.mrm.getPacketNumber_search()))

        if con == 'B':  # Active mode search
            flags = 0x00
        else:           # Passive search
            flags = 0x01

        packet.append(struct.pack('!BH', flags, len(rest)))
        packet.append(rest)
        osm.mrm.newMessage(''.join(packet), tries=4)

        if core.nmdc_back_compat:
            packet = osm.mrm.broadcastHeader('SQ', osm.me.ipp)
            packet.append(struct.pack('!I', osm.mrm.getPacketNumber_search()))

            string = "????????" + chr(flags) + rest

            if len(string) > 255:
                self.pushStatus("Search query data is too long (%s > 255) to be broadcast in this hybrid network." % len(string))
                return

            packet.append(struct.pack('!B', len(string)))
            packet.append(string)
            osm.mrm.newMessage(''.join(packet), tries=4)

        # If local searching is enabled, send the search to myself
        if self.main.state.localsearch:
            self.push_ADC_SearchRequest(self.main.osm.me, rest, flags)


    def d_RES(self, con, src_sid, dst_sid, rest):

        if not self.isOnline():
            return

        try:
            node = self.main.osm.nkm.lookupNodeFromSID(dst_sid)
        except KeyError:
            return

        if node.protocol != self.protocol:
            return

        def fail_cb(reason):
            pass

        osm = self.main.osm

        ack_key = node.getPMAckKey()

        packet = ['AR']
        packet.append(osm.me.ipp)
        packet.append(ack_key)
        packet.append(osm.me.nickHash())
        packet.append(node.nickHash())

        packet.append(struct.pack('!H', len(rest)))
        packet.append(rest)
        packet = ''.join(packet)

        node.sendPrivateMessage(self.main.ph, ack_key, packet, fail_cb)


    def d_STA(self, con, src_sid, dst_sid, rest):

        if not self.isOnline():
            return

        try:
            node = self.main.osm.nkm.lookupNodeFromSID(dst_sid)
        except KeyError:
            return

        if node.protocol != self.protocol:
            return

        def fail_cb(reason):
            pass

        osm = self.main.osm

        ack_key = node.getPMAckKey()

        packet = ['AE']
        packet.append(osm.me.ipp)
        packet.append(ack_key)
        packet.append(osm.me.nickHash())
        packet.append(node.nickHash())

        packet.append(struct.pack('!H', len(rest)))
        packet.append(rest)
        packet = ''.join(packet)

        node.sendPrivateMessage(self.main.ph, ack_key, packet, fail_cb)


    def attachMeToDtella(self):

        CHECK(self.main.dch is None)

        if self.state == 'queued':
            self.queued_dcall.cancel()
            self.queued_dcall = None
            self.pushStatus(
                "The other client left.  Resuming normal connection.")

        dcall_discard(self, 'queued_dcall')

        self.addDispatch('MSG', ('B','E'),  self.d_MSG)
        self.addDispatch('CTM', ('D'),      self.d_CTM)
        self.addDispatch('RCM', ('D'),      self.d_RCM)
        self.addDispatch('SCH', ('B','F'),  self.d_SCH)
        self.addDispatch('RES', ('D'),      self.d_RES)
        self.addDispatch('STA', ('D'),      self.d_STA)

        # Announce my presence.
        # If Dtella's online too, this will trigger an event_DtellaUp.
        self.state = 'ready'
        self.main.addDCHandler(self)


    def formatMyInfo(self, locdes=False):

        self.infdict['CT'] = '0'

        if 'VE' in self.infdict and len(self.infdict['VE']) > 0:
            verstr = get_version_string()
            if verstr not in self.infdict['VE']:
                self.infdict['VE'] = "%s;%s" % (self.infdict['VE'], verstr)
        else:
            self.infdict['VE'] = get_version_string()

        if local.use_locations:
            # Try to get my location name.
            try:
                ad = Ad().setRawIPPort(self.main.osm.me.ipp)
                loc = self.main.location[ad.getTextIP()]
            except (AttributeError, KeyError):
                loc = None

            # If I got a location name, splice it into my connection field
            if loc:
                # Append location suffix, if it exists
                suffix = self.main.state.suffix
                if suffix:
                    loc = '%s|%s' % (loc, suffix)

                self.infdict['LO'] = loc

        if locdes:
            info = adc_infostring(adc_locdes(self.infdict))
        else:
            info = adc_infostring(self.infdict)

        if len(info) > 65535:
            self.pushStatus("*** Your info string is too long!")
            info = ''

        return info


    def isLeech(self):
        # If I don't meet the minimum share, yell and return True
        osm = self.main.osm
        minshare = self.main.dcfg.minshare

        if osm.me.shared < minshare:
            self.pushStatus(
                "*** You must share at least %s in order to download!  "
                "(You currently have %s)" %
                (format_bytes(minshare), format_bytes(osm.me.shared)))
            return True

        return False


    def pushChatMessage(self, nick, text, flags=0):
        try:
            sid = self.main.osm.nkm.lookupSIDFromNick(nick)
            self.pushChatMessageBySID(sid, text, flags)
        except KeyError:
            # Pass non-DC users' messages through the hub
            # ie. users such as *, *IRC, ~ChanServ etc
            self.pushStatus("On behalf of %s: %s" % (nick, text))


    def pushChatMessageBySID(self, sid, text, flags=0):
        if flags & core.SLASHME_BIT:
            self.sendLine("BMSG %s %s ME1" % (sid, adc_escape(text)))
        else:
            self.sendLine("BMSG %s %s" % (sid, adc_escape(text)))


    def pushInfo(self, node):
        if node.sid and node.dcinfo:
            self.sendLine("BINF %s %s" % (node.sid, node.dcinfo))
        else:
            print "+ Node: %s has no dcinfo" % node.nick


    def pushTopic(self, topic=None):
        if topic:
            self.sendLine("IINF CT32 DE%s" % adc_escape(topic))
        else:
            self.sendLine("IINF CT32 DE")


    def pushQuit(self, node):
        if node.sid:
            self.sendLine("IQUI %s" % node.sid)
        else:
            print "+ Node \"%s\" has no SID" % node.nick


    def push_NMDC_ConnectToMe(self, ad, use_ssl):
        # We are recieving an NMDC $ConnectToMe so
        # create an NMDC AbortOut to deal with it
        ip, port = ad.getAddrTuple()
        from dc import AbortTransfer_Factory
        reactor.connectTCP(ip, port, AbortTransfer_Factory(self.nick))


    def push_ADC_ConnectToMe(self, node, protocol_str, port, token):
        # Reject non-crypto requests for a force-crypto network
        if self.checkForceCrypto(protocol_str):
            raise core.Reject("141 %s" % adc_escape(
                "Disallowed Protocol: Unencrypted connection"))
        self.sendLine("DCTM %s %s %s %s %s" % (node.sid, self.sid,
                            protocol_str, port, token))


    def push_NMDC_RevConnectToMe(self, nick):
        #print "$RevCTM"
        pass


    def push_ADC_RevConnectToMe(self, node, protocol_str, token):
        self.sendLine("DRCM %s %s %s %s" % (node.sid, self.sid,
                            protocol_str, token))


    def push_NMDC_SearchRequest(self, ipp, search_string):
        pass    # ignore NMDC searches as we cant respond to them


    def push_ADC_SearchRequest(self, n, search_str, flags):
        if flags & 0x1: # F context
            self.sendLine("FSCH %s %s" % (n.sid, search_str))
        else:           # B context
            self.sendLine("BSCH %s %s" % (n.sid, search_str))


    def push_ADC_SearchResponce(self, n, str):
        self.sendLine("DRES %s %s %s" % (n.sid, self.sid, str))


    def push_ADC_Error(self, n, str):
        self.sendLine("DSTA %s %s %s" % (n.sid, self.sid, str))


    def pushBotMsg(self, text):
        self.sendLine("EMSG %s %s %s PM%s" % (self.bot.sid, self.sid, adc_escape(text), self.bot.sid))


    def pushPrivMsg(self, nick, text):

        sid = self.bot.sid  # Default anything that is not a user to be from Dtella
                            # Users such as *, *IRC, ~ChanServ etc
        try:
            sid = self.main.osm.nkm.lookupSIDFromNick(nick)
        except KeyError:
            text = "On behalf of %s: %s" % (nick, text)

        self.sendLine("EMSG %s %s %s PM%s" % (sid, self.sid, adc_escape(text), sid))


    def pushStatus(self, text):
        self.sendLine("ISTA 000 %s" % (adc_escape(text)))


    def scheduleChatRateControl(self):
        if self.chatRate_dcall:
            return

        def cb():
            self.chatRate_dcall = reactor.callLater(1.0, cb)

            if self.chatq:
                args = self.chatq.pop(0)
                self.broadcastChatMessage(*args)
            else:
                self.chat_counter = min(5, self.chat_counter + 1)

        cb()


    def broadcastChatMessage(self, flags, text):

        CHECK(self.isOnline())

        osm = self.main.osm

        if osm.isModerated():
            # If the channel went moderated with something in the queue,
            # wipe it out and don't send.
            del self.chatq[:]
            return

        packet = osm.mrm.broadcastHeader('CH', osm.me.ipp)
        packet.append(struct.pack('!I', osm.mrm.getPacketNumber_chat()))

        packet.append(osm.me.nickHash())
        packet.append(struct.pack('!BH', flags | core.PROTOCOL_ADC, len(text)))
        packet.append(text)

        osm.mrm.newMessage(''.join(packet), tries=4)

        self.pushChatMessageBySID(self.sid, text, flags)

    # Precompile a regex for pushSearchResult
    searchreply_re = re.compile(r"^\$SR ([^ |]+) ([^|]*) \([^ |]+\)\|?$")
    """
    def pushSearchResult(self, data):

        m = self.searchreply_re.match(data)
        if not m:
            # Doesn't look like a search reply
            return

        nick = m.group(1)
        data = m.group(2)

        # If I get results from myself, map them to the bot's nick
        if nick == self.nick:
            nick = self.bot.nick

        self.sendLine("$SR %s %s (127.0.0.1:%d)"
                      % (nick, data, self.factory.listen_port))

    """
    def remoteNickCollision(self):

        text = (
            "*** Another node on the network has reported that your nick "
            "seems to be in a conflicting state.  This could prevent your "
            "chat and search messages from reaching everyone, so it'd be "
            "a good idea to try changing your nick.  Or you could wait "
            "and see if the problem resolves itself."
            )

        for line in word_wrap(text):
            self.pushStatus(line)


    def doRejoin(self):
        if self.state != 'invisible':
            return

        dcall_discard(self, 'autoRejoin_dcall')

        self.state = 'ready'

        # This can trigger an event_DtellaUp()
        self.main.stateChange_ObserverUp()


    def isProtectedNick(self, nick):
        return (nick.lower() in (self.nick.lower(), self.bot.nick.lower()))


    def event_DtellaUp(self):
        CHECK(self.isOnline())

        # from GetNickList - addapted to just send BINF for all online users

        me = self.main.osm.me
        me.info = self.infdict
        me.dcinfo = adc_infostring(self.infdict)
        # self.main.osm.nkm.lookupNodeFromNick(self.nick).sid = self.sid

        for node in self.main.osm.nkm.nickmap.itervalues():
            if node.nick != self.nick and node.nick != self.bot.nick and node.dcinfo is not None:
                self.pushInfo(node)

        self.sendLine("BINF %s %s" % (self.sid, me.dcinfo))

        # Grab the current topic from Dtella.
        tm = self.main.osm.tm
        self.pushTopic(tm.topic)
        if tm.topic:
            self.pushStatus(tm.getFormattedTopic())


    def event_DtellaDown(self):
        CHECK(self.isOnline())

        # Wipe out the topic
        self.pushTopic()

        # Wipe out my outgoing chat queue
        del self.chatq[:]


    def event_KickMe(self, lines, rejoin_time):
        # Sequence of events during a kick:
        # 1. event_RemoveNick(*)
        # 2. event_DtellaDown()
        # 3. event_KickMe()
        # 4. stateChange_ObserverDown()

        # Node will become visible again if:
        # - Dtella node loses its connection
        # - User types !REJOIN
        # - DC client reconnects (creates a new DCHandler)

        CHECK(self.state == 'ready')
        self.state = 'invisible'

        for line in lines:
            self.pushStatus(line)

        if rejoin_time is None:
            return

        # Automatically rejoin the chat after a timeout period.
        def cb():
            self.autoRejoin_dcall = None
            self.pushStatus("Automatically rejoining...")
            self.doRejoin()

        CHECK(self.autoRejoin_dcall is None)
        self.autoRejoin_dcall = reactor.callLater(rejoin_time, cb)


    def event_AddNick(self, n):
        pass # nothing to do - no $Hello for ADC
             # This is all done with a BINF (equv of $MyINFO $ALL)


    def event_RemoveNick(self, n, reason):
        if not self.isProtectedNick(n.nick):
            self.pushQuit(n)


    def event_UpdateInfo(self, n):
        if n.dcinfo is not None:
            self.pushInfo(n)


    def event_ChatMessage(self, n, nick, text, flags):
        self.pushChatMessage(nick, text, flags)

verifyClass(IDtellaStateObserver, ADCHandler)


# This class immediately sends the user a redirection sends disconnects them.
# Intended not for this module, but for other protocol modules that may want
# to redirect users to the correct connection address.

class ADC_AbortConnection(ADCHandler):

    def __init__(self, dch, data, cprtl, caddr):
        ADCHandler.__init__(self, dch.main)
        self.cprtl = cprtl
        self.caddr = caddr

        # Steal connection from the DCHandler
        self.factory = dch.factory
        self.makeConnection(dch.transport)
        self.transport.protocol = self

        # Steal the rest of the data
        self._buffer = dch._buffer

        # If we're not done in 5 seconds, something's fishy.
        def cb():
            self.timeout_dcall = None
            self.transport.loseConnection()

        self.timeout_dcall = reactor.callLater(5.0, cb)
        self.dataReceived(data)


    def attachMeToDtella(self):

        CHECK(self.main.dch is None)

        if self.state == 'queued':
            self.queued_dcall.cancel()
            self.queued_dcall = None
            self.pushStatus(
                "The other client left.  Resuming normal connection.")

        dcall_discard(self, 'queued_dcall')

        self.pushStatus("This node uses %s, not ADC. Please connect to %s "
            "instead." % (self.cprtl, self.caddr))

        self.timeout_dcall.reset(0)


    def connectionLost(self, reason):
        dcall_discard(self, 'timeout_dcall')


##############################################################################


class ADCFactory(ServerFactory):

    def __init__(self, main, listen_port):
        self.main = main
        self.listen_port = listen_port # spliced into search results

    def buildProtocol(self, addr):
        if addr.host != '127.0.0.1':
            return None

        p = ADCHandler(self.main)
        p.protocol = core.PROTOCOL_ADC
        p.factory = self
        return p


##############################################################################

