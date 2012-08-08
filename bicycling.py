import bcrypt
import redis
import string
import re
import os
import requests
import httplib
import json
import time
import datetime
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.schedule as schedule

class Bicycling(callbacks.Plugin):
    '''Add the help for '@plugin help Bicycling' here
    This should describe *how* to use this plugin.'''
    threaded = True
    def __init__(self, irc):
        self.__parent = super(Bicycling, self)
        self.__parent.__init__(irc)
        self.redis_server = redis.Redis('localhost')
        self.errors = {
                'about': '%s is boring as hell because I know nothing about him/her',
                'location': '%s must live on the moon',
                'photo': '%s is not pretty enough to have a photo',
                'bike': '%s must have a derpy bike because I don\'t know what it is',
                'reddit': '%s is not a redditor',
                'strava': '%s is not a Strava user',
                'lbs': '%s doesn\'t have a favorite LBS',
                'bikephoto': '%s must have non-photogenic bike because I don\'t have a picture'}
        self.replies = {
                'about': '%s wanted you to know: %s',
                'location': '%s\'s location is %s',
                'photo': '%s\'s photo is %s',
                'bike': '%s has a %s',
                'lbs': '%s\'s preferred LBS is: %s',
                'reddit': '%s has been a redditor for %s days, has %s link karma and %s comment karma',
                'strava': '%s\'s Strava Profile is %s',
                'bikephoto': 'Here is %s\'s sexy ass bike: %s'}
        self.functions = {
                'about': self._do_others ,
                'location': self._do_others ,
                'photo': self._do_others ,
                'bike': self._do_others,
                'lbs': self._do_others,
                'reddit': self._do_reddit,
                'strava': self._do_others,
                'bikephoto': self._do_others
        }

    def _default(self, irc, msg, args, text):
        cmd = msg.args[1].split()[0].lower()
        if cmd[0] in ['.','!','#']:
            cmd = cmd[1:]
        if text.split()[0] == 'set':
            #if not self._check_host(msg):
            #    irc.reply('Your hostname does not match the one last used. If this is really you, tell an op.')
            #    return
            self._set_data(msg.nick, cmd, msg.host, text[4:])
            if msg.args[0] == '#/r/bicycling':
                irc.reply('Done, but if you want to change more data please /msg me so you don\'t spam the channel.')
            else:
                irc.reply('Done')
        else:
            nick = text.split()[0]
            data = str(self._get_data(nick, cmd)).strip()
            if not data or data == 'None':
                irc.reply(self.errors[cmd] % nick)
            else:
                irc.reply(self.functions[cmd](nick, cmd))

    reddit = wrap(_default, ['text'])
    about = wrap(_default, ['text'])
    location = wrap(_default, ['text'])
    bike = wrap(_default, ['text'])
    lbs = wrap(_default, ['text'])
    photo = wrap(_default, ['text'])
    bikephoto = wrap(_default, ['text'])
    strava = wrap(_default, ['text'])

    def clear_host(self, irc, msg, args, nick):
        '''<nick>

        stuff'''
        if msg.nick in irc.state.channels[msg.args[0]].ops:
            self.redis_server.hset('users:%s' % nick.lower(), 'host', False)
            irc.reply('%s\'s hostlock has been lifted.' % nick, prefixNick=False)
        else:
            irc.reply('You need to be an op to do that.')
    clear_host = wrap(clear_host, ['nick'])

    def hold(self, irc, msg, args, offender):
        '''<nick>

        Gets <nick> a hold.
        '''
        if offender == 'bikeb0t':
            text = 'slaps %s' % msg.nick
        else:
            text = 'holds %s.' % (offender)
        irc.reply(text, prefixNick=False, action=True, to='#/r/bicycling')
    hold = wrap(hold, ['nick'])

    def beer(self, irc, msg, args, offender):
        '''<nick>

        Gets <nick> a beer.
        '''
        if offender == 'bikeb0t':
            text = 'smashes a beer over %s\'s head' % msg.nick
        else:
            text = 'gets %s a beer' % (offender)
        irc.reply(text, prefixNick=False, action=True, to='#/r/bicycling')
    beer = wrap(beer, ['nick'])

    def tea(self, irc, msg, args, offender):
        '''<nick>

        Gets <nick> a tea.
        '''
        if offender == 'bikeb0t':
            text = 'pours burning tea over %s\'s head' % msg.nick
        else:
            text = 'gets %s a tea' % (offender)
        irc.reply(text, prefixNick=False, action=True, to='#/r/bicycling')
    tea = wrap(tea, ['nick'])

    def weather(self, irc, msg, args, location):
        '''<place>

        gets weather for place or for a stored !location for a nick
        '''
        user_location = str(self._get_data(msg.args[1].split()[1], "location")).strip()
        if user_location and user_location != "None":
            irc.reply(self.getWeather(user_location))
        else:
            irc.reply(self.getWeather(location))


    weather = wrap(weather, ['text'])

    def slap(self, irc, msg, args, offender):
        '''<nick>

        Slaps <nick>.
        '''
        if offender == 'bikeb0t':
            text = 'punches %s in the face' % msg.nick
        else:
            text = 'slaps %s' % offender
        irc.reply(text, prefixNick=False, action=True, to='#/r/bicycling')
    slap = wrap(slap, ['nick'])

    def fuckshitupyo(self, irc, msg, args):
        if msg.nick in irc.state.channels[msg.args[0]].ops:
            for nick in self.redis_server.smembers('users'):
                for d in ['about','reddit','bike','location','photo']:
                    o = self.redis_server.hget('users:%s' % nick.lower(), d)
                    if o == 'None':
                        self.redis_server.hdel('users:%s' % nick.lower(), d)
            irc.reply('Shit has been fucked up.')
            irc.reply('yo')
        else:
            irc.reply('bitch please')
    fuckshitupyo = wrap(fuckshitupyo)

    def doJoin(self, irc, msg):
        self.redis_server.sadd('online_users', msg.nick)
        then = int(self.redis_server.get('last_message'))
        now = int(time.time())
        d = now - then
        minutes = d / 60
        if self.Create_user(msg.nick) and minutes > 20:
            irc.reply('Hey %s, it looks like nobody is talking now so if you \
have a question, ask it and then stick around for an answer.' % msg.nick)
        if msg.nick == "chrisinajar":
            irc.reply('Go Away %s' % msg.nick)

    def doQuit(self, irc, msg):
        self.redis_server.srem('online_users', msg.nick)
    doKick = doQuit
    doPart = doQuit

    def doPrivmsg(self, irc, msg):
        self.redis_server.set('last_message', int(time.time()))

    def Create_user(self, nick):
        return self.redis_server.sadd('users', nick.lower())

    def _get_data(self, nick, dtype):
        if dtype == 'reddit':
            return self.redis_server.hget('users:%s' % nick.lower(), dtype) or nick
        else:
            return self.redis_server.hget('users:%s' % nick.lower(), dtype)

    def _set_data(self, nick, dtype, host, data):
        self.redis_server.hset('users:%s' % nick.lower(), dtype, data)
        self.redis_server.hset('users:%s' % nick.lower(), 'host', host)

    def _do_others(self, nick, cmd):
        return self.replies[cmd] % (nick, self._get_data(nick, cmd))

    def _do_reddit(self, account, cmd):
        try:
            reddit_data = requests.get('http://www.reddit.com/user/%s/about.json' % account).text
        except:
            return 'No reddit account for %s. You can set your reddit account with !reddit set <username>' % account
        else:
            js = json.loads(reddit_data)
            made_utc = js['data']['created_utc']
            link_karma = js['data']['link_karma']
            comment_karma = js['data']['comment_karma']
            now = datetime.date.today()
            then = datetime.date.fromtimestamp(made_utc)
            age = now - then
            return self.replies['reddit'] % (account, age.days, link_karma, comment_karma)

    def _check_host(self, msg):
        host = self.redis_server.hget('users:%s' % msg.nick.lower(), 'host')
        if not host or host == msg.host:
            return True
        else:
            return False



    def getWeather(self, area_dirty):
        """
        Returns the current weather in a given location
        """
        # import re
        import xmltodict  #importing here for easy sharing.   https://github.com/martinblech/xmltodict
        try:
            area = re.sub('[\W_]+', '+', area_dirty)
            resp = requests.get('http://www.google.com/ig/api?weather=%s' % area)
            doc = xmltodict.parse(resp.text)
            weather = doc['xml_api_reply']['weather']
            current = weather['current_conditions']
            forecast = weather['forecast_information']

            # Compile the great string to say the weather.
            weather = "In %s it's %sC(%sF). The Sky is %s. Current condition of %s." % (
                forecast['city']['@data'],
                current['temp_c']['@data'],
                current['temp_f']['@data'],
                current['condition']['@data'],
                current['wind_condition']['@data'],
                #forecast['current_date_time']['@data']
            )
        except:
            return "Cannot find weather information for %s" % area_dirty
        return weather



Class = Bicycling
# vim:set shiftwidth=4 softtabstop=4 expandtab:
