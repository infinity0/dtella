"""
Dtella - Dtella Bot Module
Copyright (C) 2008  Dtella Labs (http://www.dtella.org)
Copyright (C) 2008  Paul Marks
Copyright (C) 2009  Dtella Cambridge (http://camdc.pcriot.com/)
Copyright (C) 2009  Andrew Cooper, Ximin Luo

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

from twisted.internet import reactor
from twisted.python.runtime import seconds
import twisted.python.log

from dtella.common.util import (validateNick, word_wrap, split_info,
                                split_tag, dcall_discard, cmpify_version,
                                format_bytes, dcall_timeleft,
                                get_version_string, lock2key, CHECK)
from dtella.common.ipv4 import Ad
import dtella.common.core as core
import dtella.local_config as local
import struct
import random
import re
import binascii
import socket

from zope.interface import implements
from zope.interface.verify import verifyClass
from dtella.common.interfaces import IDtellaStateObserver

class DtellaBot(object):
    # This holds the logic behind the "*Dtella" user

    def __init__(self, dch, nick):
        self.dch = dch
        self.main = dch.main
        self.nick = nick

        self.dbg_show_packets = False


    def say(self, txt):
        self.dch.pushBotMsg(txt)


    def commandInput(self, out, line, prefix=''):

        # Sanitize
        line = line.replace('\r', ' ').replace('\n', ' ')

        cmd = line.upper().split()

        if not cmd:
            return False

        try:
            f = getattr(self, 'handleCmd_' + cmd[0])
        except AttributeError:
            if prefix:
                return False
            else:
                out("Unknown command '%s'.  Type %sHELP for help." %
                    (cmd[0], prefix))
                return True

        # Filter out location-specific commands
        if not local.use_locations:
            if cmd[0] in self.location_cmds:
                return False
            
        if cmd[0] in self.freeform_cmds:
            try:
                text = line.split(' ', 1)[1]
            except IndexError:
                text = None

            f(out, text, prefix)
            
        else:
            def wrapped_out(line):
                for l in word_wrap(line):
                    if l:
                        out(l)
                    else:
                        out(" ")
           
            f(wrapped_out, cmd[1:], prefix)

        return True


    def syntaxHelp(self, out, key, prefix):

        try:
            head = self.bighelp[key][0]
        except KeyError:
            return

        out("Syntax: %s%s %s" % (prefix, key, head))
        out("Type '%sHELP %s' for more information." % (prefix, key))


    freeform_cmds = frozenset(['TOPIC','SUFFIX','DEBUG'])

    location_cmds = frozenset(['SUFFIX','USERS','SHARED','DENSE'])

    
    minihelp = [
        ("--",         "ACTIONS"),
        ("REJOIN",     "Hop back online after a kick or collision"),
        ("ADDPEER",    "Add the address of another node to your cache"),
        ("INVITE",     "Show your current IP and port to give to a friend"),
        ("REBOOT",     "Exit from the network and immediately reconnect"),
        ("TERMINATE",  "Completely kill your current Dtella process."),
        ("--",         "SETTINGS"),
        ("TOPIC",      "View or change the global topic"),
        ("SUFFIX",     "View or change your location suffix"),
        ("UDP",        "Change Dtella's peer communication port"),
        ("LOCALSEARCH","View or toggle local search results."),
        ("PERSISTENT", "View or toggle persistent mode"),
        ("--",         "INFORMATION"),
        ("VERSION",    "View information about your Dtella version."),
        ("USERS",      "Show how many users exist at each location"),
        ("SHARED",     "Show how many bytes are shared at each location"),
        ("DENSE",      "Show the bytes/user density for each location"),
        ("RANK",       "Compare your share size with everyone else"),
        ]


    bighelp = {
        "REJOIN":(
            "",
            "If you are kicked from the chat system, or if you attempt to use "
            "a nick which is already occupied by someone else, your node "
            "will remain connected to the peer network in an invisible state. "
            "If this happens, you can use the REJOIN command to hop back "
            "online.  Note that this is only useful after a nick collision "
            "if the conflicting nick has left the network."
            ),

        "TOPIC":(
            "<text>",
            "If no argument is provided, this command will display the "
            "current topic for the network.  This is the same text which "
            "is shown in the title bar.  If you provide a string of text, "
            "this will attempt to set a new topic.  Note that if Dtella "
            "is bridged to an IRC network, the admins may decide to lock "
            "the topic to prevent changes."
            ),

        "SUFFIX":(
            "<suffix>",
            "This command appends a suffix to your location name, which "
            "is visible in the Speed/Connection column of everyone's DC "
            "client.  Typically, this is where you put your room number. "
            "If you provide no arguments, this will display the "
            "current suffix.  To clear the suffix, just follow the command "
            "with a single space."
            ),

        "TERMINATE":(
            "",
            "This will completely kill your current Dtella node.  If you "
            "want to rejoin the network afterward, you'll have to go "
            "start up the Dtella program again."
            ),

        "VERSION":(
            "",
            "This will display your current Dtella version number.  If "
            "available, it will also display the minimum required version, "
            "the newest available version, and a download link."
            ),

        "LOCALSEARCH":(
            "<ON | OFF>",
            "If local searching is enabled, then when you search, you will "
            "see search results from the *Dtella user, which are actually "
            "hosted on your computer.  Use this command without any arguments "
            "to see whether local searching is currently enabled or not."
            ),

        "USERS":(
            "",
            "This will list all the known locations, and show how many "
            "people are currently connecting from each."
            ),

        "SHARED":(
            "",
            "This will list all the known locations, and show how many "
            "bytes of data are being shared from each."
            ),
        
        "DENSE":(
            "",
            "This will list all the known locations, and show the calculated "
            "share density (bytes-per-user) for each."
            ),
        
        "RANK":(
            "<nick>",
            "Compare your share size with everyone else in the network, and "
            "show which place you're currently in.  If <nick> is provided, "
            "this will instead display the ranking of the user with that nick."
            ),
        
        "UDP":(
            "<port>",
            "Specify a port number between 1-65536 to change the UDP port "
            "that Dtella uses for peer-to-peer communication.  If you don't "
            "provide a port number, this will display the port number which "
            "is currently in use."
            ),

        "ADDPEER":(
            "<ip>:<port>",
            "If Dtella is unable to locate any neighbor nodes using the "
            "remote config data or your local neighbor cache, then you "
            "can use this command to manually add the address of an existing "
            "node that you know about."
            ),
            
        "INVITE":(
            "",
            "If you wish to invite another user to join the network using the "
            "!ADDPEER command, you can use this command to retrieve your "
            "current IP and port to give to them to use."
            ),

        "REBOOT":(
            "",
            "This command takes no arguments.  It will cause your node to "
            "exit from the network, and immediately restart the connection "
            "process.  Use of this command shouldn't be necessary for "
            "normal operation."
            ),

        "PERSISTENT":(
            "<ON | OFF>",
            "This option controls how Dtella will behave when it is not "
            "attached to a Direct Connect client.  When PERSISTENT mode is "
            "OFF, Dtella will automatically close its peer connection after "
            "5 minutes of inactivity.  When this mode is ON, Dtella will "
            "try to stay connected to the network continuously.  To see "
            "whether PERSISTENT is enabled, enter the command with no "
            "arguments."
            )
        }


    def handleCmd_HELP(self, out, args, prefix):

        if len(args) == 0:
            out("This is your local Dtella bot.  You can send messages here "
                "to control the various features of Dtella.  A list of "
                "commands is provided below.  Note that you can PM a command "
                "directly to the %s user, or enter it in the main chat "
                "window prefixed with an exclamation point (!)" % self.nick)

            for command, description in self.minihelp:

                # Filter location-specific commands
                if not local.use_locations:
                    if command in self.location_cmds:
                        continue
                
                if command == "--":
                    out("")
                    out("  --%s--" % description)
                else:
                    out("  %s%s - %s" % (prefix, command, description))

            out("")
            out("For more detailed information, type: "
                "%sHELP <command>" % prefix)

        else:
            key = ' '.join(args)

            # If they use a !, strip it off
            if key[:1] == '!':
                key = key[1:]

            try:
                # Filter location-specific commands
                if not local.use_locations:
                    if key in self.location_cmds:
                        raise KeyError
                    
                (head, body) = self.bighelp[key]
                
            except KeyError:
                out("Sorry, no help available for '%s'." % key)

            else:
                out("Syntax: %s%s %s" % (prefix, key, head))
                out("")
                out(body)


    def handleCmd_REBOOT(self, out, args, prefix):

        if len(args) == 0:
            out("Rebooting Node...")
            self.main.shutdown(reconnect='instant')
            return

        self.syntaxHelp(out, 'REBOOT', prefix)


    def handleCmd_UDP(self, out, args, prefix):
        if len(args) == 0:
            out("Dtella's UDP port is currently set to: %d"
                % self.main.state.udp_port)
            return

        elif len(args) == 1:
            try:
                port = int(args[0])
                if not 1 <= port <= 65535:
                    raise ValueError
            except ValueError:
                pass
            else:
                out("Changing UDP port to: %d" % port)
                self.main.changeUDPPort(port)
                return
            
        self.syntaxHelp(out, 'UDP', prefix)


    def handleCmd_ADDPEER(self, out, args, prefix):

        if len(args) == 1:
            try:
                ad = Ad().setTextIPPort(args[0])
            except ValueError:
                pass
            else:
                if not ad.port:
                    out("Port number must be nonzero.")
                    
                elif ad.auth('sx', self.main):
                    self.main.state.refreshPeer(ad, 0)
                    out("Added to peer cache: %s" % ad.getTextIPPort())

                    # Jump-start stuff if it's not already going
                    self.main.startConnecting()
                else:
                    out("The address '%s' is not permitted on this network."
                        % ad.getTextIPPort())
                return

        self.syntaxHelp(out, 'ADDPEER', prefix)
        
    
    def handleCmd_INVITE(self, out, args, prefix):
        
        if len(args) == 0:
            osm = self.main.osm
            if osm:
                out("Tell your friend to enter the following into their client "
                    "to join the network:")
                out("")
                out("  !addpeer %s"
                    % Ad().setRawIPPort(osm.me.ipp).getTextIPPort())
                out("")
            else:
                out("You cannot invite someone until you are connected to the "
                    "network yourself.")
            return
        
        self.syntaxHelp(out, 'INVITE', prefix)
        

    def handleCmd_PERSISTENT(self, out, args, prefix):
        if len(args) == 0:
            if self.main.state.persistent:
                out("Persistent mode is currently ON.")
            else:
                out("Persistent mode is currently OFF.")
            return

        if len(args) == 1:
            if args[0] == 'ON':
                out("Set persistent mode to ON.")
                self.main.state.persistent = True
                self.main.state.saveState()

                if self.main.osm:
                    self.main.osm.updateMyInfo()

                self.main.startConnecting()
                return

            elif args[0] == 'OFF':
                out("Set persistent mode to OFF.")
                self.main.state.persistent = False
                self.main.state.saveState()

                if self.main.osm:
                    self.main.osm.updateMyInfo()
                return

        self.syntaxHelp(out, 'PERSISTENT', prefix)


    def handleCmd_LOCALSEARCH(self, out, args, prefix):
        if len(args) == 0:
            if self.main.state.localsearch:
                out("Local searching is currently ON.")
            else:
                out("Local searching is currently OFF.")
            return

        if len(args) == 1:
            if args[0] == 'ON':
                out("Set local searching to ON.")
                self.main.state.localsearch = True
                self.main.state.saveState()
                return

            elif args[0] == 'OFF':
                out("Set local searching to OFF.")
                self.main.state.localsearch = False
                self.main.state.saveState()
                return

        self.syntaxHelp(out, 'LOCALSEARCH', prefix)


    def handleCmd_REJOIN(self, out, args, prefix):

        if len(args) == 0:

            if self.dch.state != 'invisible':
                out("Can't rejoin: You're not invisible!")
                return

            out("Rejoining...")
            self.dch.doRejoin()
            return
        
        self.syntaxHelp(out, 'REJOIN', prefix)


    def handleCmd_USERS(self, out, args, prefix):

        if not self.dch.isOnline():
            out("You must be online to use %sUSERS." % prefix)
            return
        
        self.showStats(
            out,
            "User Counts",
            lambda u,b: u,
            lambda v: "%d" % v,
            peers_only=False
            )


    def handleCmd_SHARED(self, out, args, prefix):

        if not self.dch.isOnline():
            out("You must be online to use %sSHARED." % prefix)
            return
        
        self.showStats(
            out,
            "Bytes Shared",
            lambda u,b: b,
            lambda v: "%s" % format_bytes(v),
            peers_only=True
            )


    def handleCmd_DENSE(self, out, args, prefix):

        if not self.dch.isOnline():
            out("You must be online to use %sDENSE." % prefix)
            return

        def compute(u,b):
            try:
                return (b/u, u)
            except ZeroDivisionError:
                return (0, u)
        
        self.showStats(
            out,
            "Share Density",
            compute,
            lambda v: "%s/user (%d)" % (format_bytes(v[0]), v[1]),
            peers_only=True
            )


    def handleCmd_RANK(self, out, args, prefix):

        if not self.dch.isOnline():
            out("You must be online to use %sRANK." % prefix)
            return

        osm = self.main.osm

        tie = False
        rank = 1

        target = None

        if len(args) == 0:
            target = osm.me
        elif len(args) == 1:
            try:
                target = osm.nkm.lookupNodeFromNick(args[0])
            except KeyError:
                out("The nick <%s> cannot be located." % args[0])
                return
        else:
            self.syntaxHelp(out, 'RANK', prefix)
            return
        
        if target is osm.me:
            who = "You are"
        else:
            who = "%s is" % target.nick

        for n in osm.nkm.nickmap.values():
            if n is target:
                continue

            if n.shared > target.shared:
                rank += 1
            elif n.shared == target.shared:
                tie = True

        try:
            suffix = {1:'st',2:'nd',3:'rd'}[rank % 10]
            if 11 <= (rank % 100) <= 13:
                raise KeyError
        except KeyError:
            suffix = 'th'

        if tie:
            tie = "tied for"
        else:
            tie = "in"

        out("%s %s %d%s place, with a share size of %s." %
            (who, tie, rank, suffix, format_bytes(target.shared))
            )
        
    def handleCmd_TOPIC(self, out, topic, prefix):
        
        if not self.dch.isOnline():
            out("You must be online to use %sTOPIC." % prefix)
            return

        tm = self.main.osm.tm

        if topic is None:
            out(tm.getFormattedTopic())
        else:
            out(None)
            tm.broadcastNewTopic(topic)


    def handleCmd_SUFFIX(self, out, text, prefix):

        if text is None:
            out("Your location suffix is \"%s\"" % self.main.state.suffix)
            return

        text = text[:8].rstrip().replace('$','')

        self.main.state.suffix = text
        self.main.state.saveState()
        
        out("Set location suffix to \"%s\"" % text)

        osm = self.main.osm
        if osm:
            osm.updateMyInfo()


    def showStats(self, out, title, compute, format, peers_only):

        CHECK(self.dch.isOnline())

        # Count users and bytes
        ucount = {}
        bcount = {}

        # Collect user count and share size
        for n in self.main.osm.nkm.nickmap.values():

            if peers_only and not n.is_peer:
                continue
            
            try:
                ucount[n.location] += 1
                bcount[n.location] += n.shared
            except KeyError:
                ucount[n.location] = 1
                bcount[n.location] = n.shared

        # Collect final values
        values = {}
        for loc in ucount:
            values[loc] = compute(ucount[loc], bcount[loc])

        # Sort by value, in descending order
        locs = values.keys()
        locs.sort(key=lambda loc: values[loc], reverse=True)

        overall = compute(sum(ucount.values()), sum(bcount.values()))

        # Build info string and send it
        out("/== %s, by Location ==\\" % title)
        for loc in locs:
            out("| %s <= %s" % (format(values[loc]), loc))
        out("|")
        out("\\_ Overall: %s _/" % format(overall))


    def handleCmd_VERSION(self, out, args, prefix):
        if len(args) == 0:
            out("You have Dtella version %s." % local.version)

            if self.main.dcfg.version:
                min_v, new_v, url, repo = self.main.dcfg.version
                out("The minimum required version is %s." % min_v)
                out("The latest posted version is %s." % new_v)
                out("Download Link: %s" % url)

            return

        self.syntaxHelp(out, 'VERSION', prefix)


    def handleCmd_TERMINATE(self, out, args, prefix):
        if len(args) == 0:
            reactor.stop()
            return

        self.syntaxHelp(out, 'TERMINATE', prefix)


    def handleCmd_VERSION_OVERRIDE(self, out, text, prefix):
        if self.main.dcfg.overrideVersion():
            out("Overriding minimum version!  Don't be surprised "
                "if something breaks.")
            self.main.startConnecting()
        else:
            out("%sVERSION_OVERRIDE not needed." % prefix)


    def handleCmd_UPGRADE(self, out, text, prefix):
        min_v, new_v, url, repo = self.main.dcfg.version
        if cmpify_version(new_v) <= cmpify_version(local.version):
            out("You are already at the newest version.")
            return

        if local.build_suffix not in ["tar.bz2", "dmg", "exe"]:
            out("Upgrade not supported for build type %s" % local.build_suffix)
            return

        import os, urllib, sys, subprocess

        new_p = local.build_prefix + new_v
        binurl = url + repo + new_p + "." + local.build_suffix

        out("Upgrading from %s to %s" % (local.version, new_v))

        out("- Downloading %s" % binurl)
        try:
            fpath, headers = urllib.urlretrieve(binurl)
        except Exception, e:
            out("Error: Couldn't download the update: %s" % e)
            return

        try:
            if local.build_suffix == 'tar.bz2':
                import sys, time, shutil

                bk_sep = '-'
                basep = sys.path[0] + os.sep
                bkup = local.build_prefix + local.version + bk_sep + \
                    str(int(time.time())) + os.sep
                blist = os.listdir(basep)
                out("- Backing up current dtella to %s" % bkup)
                bkup = basep + bkup
                try:
                    # TODO: the following only works in python 2.6:
                    # shutil.copytree(basep, basep + bkup, True,
                    #    basep + local.build_prefix + local.version + "-*")
                    os.mkdir(bkup)
                    for d in blist:
                        if local.build_prefix + local.version + bk_sep in d:
                            continue
                        src = basep + d
                        dst = bkup + d
                        if os.path.islink(src):
                            os.symlink(os.readlink(src), dst)
                        elif os.path.isdir(src):
                            shutil.copytree(src, dst, True)
                        else:
                            shutil.copy2(src, dst)
                except Exception, e:
                    out("Error: Backup failed: %s" % e)
                    return

                out("- Extracting tar.bz2 archive to %s" % basep)
                try:
                    import tarfile
                    tar = tarfile.open(fpath)
                    # verify that the dtella package exists
                    tar.getmember(new_p + os.sep)
                    tar.extractall(basep)
                    tar.close()
                except Exception, e:
                    out("Error: could not extract archive: %s" % e)
                    return

                out("- Installing new dtella")
                try:
                    srcp = basep + new_p + os.sep
                    try:
                        for d in os.listdir(srcp):
                            src = srcp + d
                            dst = basep + d
                            if d in blist:
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                    except Exception, e:
                        out("Error: Install failed: %s" % e)
                        out("- Restoring backup")
                        try:
                            ilist = os.listdir(basep)
                            for d in os.listdir(bkup):
                                src = bkup + d
                                dst = basep + d
                                if d in ilist:
                                    if os.path.isdir(dst):
                                        shutil.rmtree(dst)
                                    else:
                                        os.remove(basep + d)
                                if os.path.islink(src):
                                    os.symlink(os.readlink(src), dst)
                                elif os.path.isdir(src):
                                    shutil.copytree(src, dst, True)
                                else:
                                    shutil.copy2(src, dst)
                        except Exception, e:
                            out("Error: Sorry! Restore failed: %s" % e)
                        return

                finally:
                    out("- Cleaning up extracted files")
                    try:
                        shutil.rmtree(srcp)
                    except:
                        out("Warning: %s could not be fully removed: %s" % (srcp, e))
                        out("You may want to remove it manually.")

                out("- Install complete. A backup of the old installation is at %s" % bkup)


            elif local.build_suffix == 'dmg':
                out("NOT IMPLEMENTED YET")
                return # python: finally clause is executed "on the way out"


            elif local.build_suffix == 'exe':
                out("NOT IMPLEMENTED YET")
                return # python: finally clause is executed "on the way out"


        finally:
            out("- Cleaning up downloaded file")
            try:
                os.remove(fpath)
            except Exception, e:
                out("Warning: %s could not be removed: %s" % (fpath, e))
                out("You may want to remove it manually.")

        out("- Upgrade completed. Running new Dtella...")
        try:
            # opens child process with same args and env.
            # child keeps going even when this exits
            subprocess.Popen(sys.argv)
            out("The new Dtella is running. This one will shortly disconnect "
                "and exit. Once it does, you will be able to connect to the "
                "upgraded node (reconnect is ctrl-R on most clients).")
        except Exception, e:
            out("Could not automatically start the new Dtella node: %s" % e)
            out("Try doing this yourself.")


    def handleCmd_DEBUG(self, out, text, prefix):

        out(None)
        
        if not text:
            return

        text = text.strip().lower()
        args = text.split()

        if args[0] == "nbs":
            self.debug_neighbors(out)

        elif args[0] == "nodes":
            try:
                sortkey = int(args[1])
            except (IndexError, ValueError):
                sortkey = 0
            self.debug_nodes(out, sortkey)

        elif args[0] == "packets":
            if len(args) < 2:
                pass
            elif args[1] == "on":
                self.dbg_show_packets = True
            elif args[1] == "off":
                self.dbg_show_packets = False

        elif args[0] == "killudp":
            self.main.ph.transport.stopListening()


    def debug_neighbors(self, out):

        osm = self.main.osm
        if not osm:
            return

        out("Neighbor Nodes: {direction, ipp, ping, nick}")

        for pn in osm.pgm.pnbs.itervalues():
            info = []

            if pn.outbound and pn.inbound:
                info.append("<->")
            elif pn.outbound:
                info.append("-->")
            elif pn.inbound:
                info.append("<--")

            info.append(binascii.hexlify(pn.ipp).upper())

            if pn.avg_ping is not None:
                delay = pn.avg_ping * 1000.0
            else:
                delay = 0.0
            info.append("%7.1fms" % delay)

            try:
                nick = osm.lookup_ipp[pn.ipp].nick
            except KeyError:
                nick = ""
            info.append("(%s)" % nick)

            out(' '.join(info))


    def debug_nodes(self, out, sortkey):

        osm = self.main.osm
        if not (osm and osm.syncd):
            out("Not syncd")
            return

        me = osm.me

        now = seconds()

        out("Online Nodes: {ipp, nb, persist, expire, uptime, dttag, nick}")

        lines = []

        for n in ([me] + osm.nodes):
            info = []
            info.append(binascii.hexlify(n.ipp).upper())

            if n.ipp in osm.pgm.pnbs:
                info.append("Y")
            else:
                info.append("N")

            if n.persist:
                info.append("Y")
            else:
                info.append("N")

            if n is me:
                info.append("%4d" % dcall_timeleft(osm.sendStatus_dcall))
            else:
                info.append("%4d" % dcall_timeleft(n.expire_dcall))

            info.append("%8d" % (now - n.uptime))
            info.append("%8s" % n.dttag[3:])
            info.append("(%s)" % n.nick)

            lines.append(info)

        if 1 <= sortkey <= 7:
            lines.sort(key=lambda l: l[sortkey-1])

        for line in lines:
            out(' '.join(line))
