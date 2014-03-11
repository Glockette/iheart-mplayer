#! /usr/bin/env python3

import urllib.request
import urllib.parse
import json

def station_info (station_id):
	''' Returns a dict containing all available information about station_id

	station_id is a five-digit number assigned to an iHeartRadio station.
	No publicly documented method of obtaining a list of valid station_ids
	is currently available.
	'''

	# The iheartradio API is not publicly documented, to my knowledge. At the time
	# of writing, one can submit a POST request with a content of '1' to a URL of
	# the following form (where STATION_ID_NUMBER is a five-digit number):
	#
	# http://iheart.com/a/live/station/STATION_ID_NUMBER/stream/
	#
	# The response will be UTF-8 encoded JSON describing some vital information
	# about the station (if it exists), such as name, market, genre, and links to
	# various live streams of its content (often RTMP or HTTP, but usually (never?)
	# both). Valid station ID numbers can currently be obtained by searching for
	# stations on the http://iheart.com website - for example, in the following
	# URL, the station ID number is 1165:
	#
	# http://www.iheart.com/live/WOOD-Radio-1069-FM-1300AM-1165/

	# The base URL for our API request
	iheart_base_url = 'http://www.iheart.com/a/live/station/'

	# The postfix for our API request URL (comes after the ID number)
	iheart_url_postfix = 'stream/'

	# We can't do this in one function call, since urljoin can't deal with
	# more than two URL components.
	iheart_url = urllib.parse.urljoin (iheart_base_url, (str(station_id) + '/'))
	iheart_url = urllib.parse.urljoin (iheart_url, iheart_url_postfix)

	response = urllib.request.urlopen (iheart_url, '1'.encode('utf-8'))

	# We assume we're dealing with UTF-8 encoded JSON, if we aren't the API
	# has probably changed in ways we can't deal with.
	assert (response.getheader('Content-Type') == 'application/json; charset=utf-8')

	station = json.loads (response.read().decode('utf-8'))

	if (not station['ok']):
		raise RuntimeError(station['error'])
	else:
		return station

def detect_stream (station):
	'''Takes a station dictionary and determines the best stream URL to use,
	returns its URL.
	'''

	# There are two keys within the station dictionary which contain dicts
	# of stream URLs. The first is 'stream_urls', which seems to always have
	# at least two members - 'rtmp' (which is an RTMP URL which VLC and some
	# mplayer versions don't seem to understand) and 'http' (which is an
	# HTTP URL which neither mplayer or vlc seem to understand in any case I
	# have tested). Quite often, at least one of these will be None (but
	# both are always present for a valid station). For our purposes we will
	# ignore this member. The second is 'streams', which *only* contains
	# members for those streams which actually exist (there will never be a
	# None in this dict). Keys which have been observed:
	#
	# shoutcast_stream: Seems to always be a standard shoutcast stream URL.
	#                   Widely understood and works in both VLC and mplayer,
	#                   as far as I've tested.
	#
	# secure_rtmp_stream: An RTMP URL, not always the same as the RTMP URL
	#                     in stream_urls. In cases I've seen it's more
	#                     likely to work than the RTMP URL in stream_urls,
	#                     but some mplayers still don't like it (VLC seems
	#                     fine).
	#
	# stw_stream: Some kind of special HTTP-based stream, which neither
	#             mplayer or VLC understand. Seems related to the (former?)
	#             StreamTheWorld Flash-based platform, always(?) seems to
	#             occur together with pls_stream.
	#
	# pls_stream: Contains a link to a PLS file (INI-based playlist). Occurs
	#             alongside stw_stream. Seems to contain a large number of
	#             HTTP links, none of which are the same as stw_stream.
	#             Seems to work in VLC, but not any mplayer I have tested.
	#
	# Stations tend to have either both of the first two, OR both of the
	# second two. There may be others I have not encountered - dictionary
	# dumps (use -vv) of stations with other stream types would be greatly
	# appreciated.


	# For our purposes, the preference order is:
	# shoutcast_stream
	# pls_stream
	# secure_rtmp_stream
	# stw_stream
	#
	# stw_stream will print a warning, since it is not known to work in any
	# player.
	preference_order = ['shoutcast_stream',
	                    'pls_stream',
	                    'secure_rtmp_stream',
	                    'stw_stream']

	stream_dict = station['streams']


	for candidate in preference_order:
		try:
			choice = stream_dict[candidate]
			print ("stream type auto: using " + candidate)
			break
		except KeyError:
			pass
	else:
		# we have an stw_stream - almost certain to not work
		print ("warning: using stw_stream, this stream type is not known to work anywhere")
	return choice

def get_station_url (station, stream_type):
	'''Takes a station dictionary and a stream type, and returns a URL.
	Caller should be prepared for possible KeyErrors, since iheartradio
	completely omits non-existent streams instead of setting their values
	to null/None. If the stream type is 'auto', a stream will be detected
	automatically using detect_stream().
	'''

	station_url = None

	# If a stream does not exist, iheart seems to just omit its entry from
	# the 'streams' category in JSON. Therefore we will bail out with a
	# KeyError if the requested stream does not exist.
	if (stream_type == 'auto'):
		station_url = detect_stream (station)
	elif (stream_type == 'rtmp'):
		if (station['streams']['secure_rtmp_stream']):
			station_url = station['streams']['secure_rtmp_stream']
	elif (stream_type == 'shout'):
		if (station['streams']['shoutcast_stream']):
			station_url = station['streams']['shoutcast_stream']
	elif (stream_type == 'stw'):
		if (station['streams']['stw_stream']):
			print ("warning: using stw_stream, this stream type is not known to work anywhere")
			station_url = station['streams']['stw_stream']
	elif (stream_type == 'pls'):
		if (station['streams']['pls_stream']):
			station_url = station['streams']['pls_stream']

	# Apparently we don't usually get here, see above.
	if (not station_url):
		raise RuntimeError ("Requested stream does not exist")

	return station_url
