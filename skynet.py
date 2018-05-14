#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# todo: clean up

import sys, codecs, time, random, re

from cobe.brain import Brain
from twisted.internet import reactor, protocol, defer
from twisted.words.protocols import irc
from twisted.python import log

UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)

#server = ['irc.quakenet.org',6667]
#channels = '#skittie'


replyrate = 50

chans = ['#test']

ircnames = []

class Bot(irc.IRCClient):
	'''	def _get_nickname(self):
		return self.factory.nick
	nickname = property(_get_nickname)
	'''

	def __init__(self, *args, **kwargs):
		self._namescallback = {}

	def got_names(self,nicklist):
		self.ircnames = nicklist
		print nicklist
		self.ircnames = [s.replace('@','') for s in nicklist]
		self.ircnames = [s.strip('+') for s in nicklist]
		print self.ircnames

	def names(self, channel):
		channel = channel.lower()
		d = defer.Deferred()
		if channel not in self._namescallback:
			self._namescallback[channel] = ([], [])

		self._namescallback[channel][0].append(d)
		self.sendLine("NAMES %s" % channel)
		return d

	def irc_RPL_NAMREPLY(self, prefix, params):
		channel = params[2].lower()
		nicklist = params[3].split(' ')

		if channel not in self._namescallback:
			return

		n = self._namescallback[channel][1]
		n += nicklist

	def irc_RPL_ENDOFNAMES(self, prefix, params):
		channel = params[1].lower()
		if channel not in self._namescallback:
			return

		callbacks, namelist = self._namescallback[channel]

		for cb in callbacks:
			cb.callback(namelist)

		del self._namescallback[channel]
        
    # START

	def connectionMade(self):
		self.nickname = self.factory.nick
		self.password = self.factory.password
		self.replyrate = self.factory.replyrate
		self.ignored = self.factory.ignored
		self.trusted = self.factory.trusted
		
		irc.IRCClient.connectionMade(self)
		print("Connected")
		
		print("Using brain %s" % self.factory.brain)
		self.brain = Brain(self.factory.brain)


	def connectionLost(self,reason):
		print("Disconnected: %s" % reason)
		irc.IRCClient.connectionLost(self,reason)
		
	def signedOn(self):
		print("Signed on as %s" % self.nickname)
		for channel in self.factory.channels:
			self.join(channel)
			
	def userJoined(self,user,channel):
		print("userjoined "+user+" "+channel)
		nick = user.split('!')[0]
		reply = self.brain.reply("")
		time.sleep(1)
		self.msg(channel,nick+": "+reply)
		print(">>> [%s] %s" % (channel,reply))
			
	def joined(self, channel):
		print("Joined %s" % channel)
		self.names(channel).addCallback(self.got_names)
		print self.names(channel)
		
	def msg(self, user, message, length = None):
		if type(message) is unicode:
			message = message.encode('utf-8')
		irc.IRCClient.msg(self, user, message, length)


	def privmsg(self,user,channel,msg):
		msg = msg.decode('utf-8')
		who = user if channel == self.nickname else channel
		nick = user.split('!')[0]
		print(user)
		print("<<< [%s] <%s> %s" % (who, nick,msg))

		if nick == self.nickname:
			return

		replyrate = self.replyrate
		if msg.startswith(self.nickname):
			msg.replace(self.nickname+":","")
			replyrate = 100
			
#		msg.replace(self.nickname, "#nick")
		
#		escaped_users = map(re.escape, self.ircnames)
#		p = re.compile(r'\b(' + ('|'.join(escaped_users)) + r')\b')
#		msg = p.sub('skynet', msg)

		
		
		# reply
		reply = self.brain.reply(msg)
		reply = reply.replace("#nick :", "#nick:")
		reply = reply.replace("#nick", nick)
		reply = reply.replace(self.nickname, nick)
				
		if msg.startswith('!!') and user in self.trusted:
			command = msg.lstrip('!').split(' ')
			print(command)
			try:
				if command[0] == 'replyrate':
					if len(command) > 1:
						self.replyrate = int(command[1])
						self.msg(who,"Now replying to "+str(self.replyrate)+"% of messages")
					else:
						self.msg(who,"Replying to "+str(self.replyrate)+"% of messages")
						
				elif command[0] == 'ignore':
					if len(command) > 1:
						self.ignored + command[1]
					self.msg(who,str(self.ignored))
					
				elif command[0] == 'unignore':
					if len(command) > 1:
						self.ignored.remove(command[1])
					self.msg(who,str(self.ignored))
					
				elif command[0] == 'reload':
					self.brain = Brain(self.factory.brain)
					self.msg(who,"done")
					
				elif command[0] == 'quit':
					self.quit("mo :D")
					sys.exit()
					
				elif command[0] == 'join':
					self.join(command[1])
					
				elif command[0] == 'leave' or command[0] == 'part':
					self.leave(command[1])
					
			except Exception, e:
				self.msg(who,str(e))
				
			return
			
		if random.random()*100 < replyrate:
			if not nick in self.ignored:
				self.msg(who,reply)
				print(">>> [%s] %s" % (who,reply))
			else:
				print("Ignoring %s" % nick)
				
		self.brain.learn(msg)
#		print u"%s".encode('utf-8') % b.reply(msg)

class BotFactory(protocol.ClientFactory):
	protocol = Bot

	def __init__(self, nick, channels, trusted, password=None, brain="cobe.brain", replyrate=33, ignored = ['yuoppo']):
			
		self.nick = nick
		self.channels = channels
		self.trusted = trusted
		self.password = password
		self.brain = brain
		self.replyrate = replyrate
		self.ignored = ignored
		
	def clientConnectionLost(self,connector,reason):
		print("Connection lost. Reason: %s" % reason)
		time.sleep(10)
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print("Connection failed. Reason: %s" % reason)


#log.startLogging(sys.stdout)

def main():
	from optparse import OptionParser
	parser = OptionParser(usage="usage: %prog [options] channels")

	parser.add_option("-s", "--server", action="store", dest="server", default="irc.quakenet.org", help="IRC server to connect to")
	parser.add_option("-p", "--port", action="store", type="int", dest="port", default=6667, help="IRC server to connect to")
	parser.add_option("-n", "--nick", action="store", dest="nick", default="skynet", help="Nickname to use")
	parser.add_option("--password", action="store", dest="password", default=None, help="server password")
	parser.add_option("-b", "--brain", action="store", dest="brain", default="cobe.brain", help="Brain file to use")
	
	parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="enable verbose output")
	parser.add_option("-t", "--trust", action="append", dest="trusted", default=["skittie!emilia@nupit.se8.fi"], help="trusted hostmasks (admin)")
	print(parser.parse_args())
	(options, channels) = parser.parse_args()
	
	if not channels:
		channels = chans
#		parser.error("You must specify a channel to join.")
		
	if options.verbose:
		log.startLogging(sys.stdout)
	
	factory = BotFactory(options.nick, channels, options.trusted, options.password)
	reactor.connectTCP(options.server, options.port, factory)
	reactor.run()

if __name__ == "__main__":
	main()
