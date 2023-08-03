import spotipy
from spotipy.oauth2 import SpotifyOAuth

import hikari
import lightbulb
from lightbulb.ext import tasks

import schedule
import time
import os

from keep_alive import keep_alive

keep_alive()

bot = lightbulb.BotApp(
  token=os.environ['DiscordBotToken'],
  intents=hikari.Intents.ALL,
  default_enabled_guilds=(os.environ['NotificationChatRoom'])
)

tasks.load(bot)

dict_messages = ''

usernames = ['Daiki', 'Shigeru']

user_info = {
    'Daiki' : {
        'client_id': os.environ['DaikiClientID'],
        'client_secret' : os.environ['DaikiClientSecret']
    }, 
    'Shigeru' : {
        'client_id': os.environ['ShigeruClientID'],
        'client_secret' : os.environ['ShigeruClientSecret']
    }
}

# Change this to your redirect_url
redirect_url='http://localhost:3000'
scope = "user-read-recently-played", "user-read-playback-state", "user-top-read", "user-read-private", "user-library-read", "playlist-modify-private", "playlist-read-private", "user-modify-playback-state"

def LoadPlaylist(sp, PlaylistName):
    uri = GetPlaylistUri(sp, PlaylistName)
    playlist = sp.playlist(playlist_id=uri)
    playlist_uri = playlist['uri']
    return playlist_uri

def GetSongsUriinPlaylist(sp, PlaylistName):
    load_uris = []
    playlist_uri = LoadPlaylist(sp, PlaylistName)
    songs = sp.playlist_items(playlist_id=playlist_uri)
    for song in songs['items']:
        uri = song['track']['uri']
        load_uris.append(uri)
    return load_uris

def GetCountinPlaylist(sp, PlaylistName):
    playlist_uri = LoadPlaylist(PlaylistName)
    playlist_details = sp.playlist(playlist_id=playlist_uri)
    count = playlist_details['tracks']['total']
    return count

def MakingPlaylist(sp, PlaylistName):
    names=[]
    results = sp.current_user_playlists()
    for result in results['items']:
        name = result['name']
        names.append(name)
    if not PlaylistName in names:
        sp.user_playlist_create(user=sp.me()['id'], name=PlaylistName, public=False, collaborative=False, description=f'my {PlaylistName} playlist')
        print("created")
    else:
        print("existed")

def GetPlaylistUri(sp, PlaylistName):
    results = sp.current_user_playlists()
    for result in results['items']:
        if PlaylistName == result['name']:
            uri = result['uri']
            return uri

def AddTopSongs(sp, PlaylistName, load_uris, PlaylistDict):
    uris = []
    results = sp.current_user_top_tracks(limit=20, offset=0, time_range=PlaylistName)
    for number, result in enumerate(results['items']):
        uri = result['uri']
        uris.append(uri)
    if load_uris == uris:
        message = 'spotify playlists were not modified!'
        print('does not change')
        PlaylistDict[PlaylistName] = 'not modified'
    else:
        DeleteAllSongsinThePlaylist(sp, PlaylistName, load_uris)
        sp.playlist_add_items(playlist_id=GetPlaylistUri(sp, PlaylistName), items=uris)
        message = 'spotify playlists were modified!:heart_eyes:'
        print('modified')
        PlaylistDict[PlaylistName] = 'modified'
    return message

def DeleteAllSongsinThePlaylist(sp, PlaylistName, load_uris):
    sp.playlist_remove_all_occurrences_of_items(playlist_id=GetPlaylistUri(sp, PlaylistName), items=load_uris)

def GetHistory(sp):
    uris_history = []
    songs = sp.current_user_recently_played()
    for song in songs['items']:
        uri = song['track']['uri']
        uris_history.append(uri)
    return uris_history

def AddPlayHistory(sp, PlaylistName, uris_history, load_uris_history_playlist):
    message_add = 'My Histroy was not updated!!'
    if not uris_history == load_uris_history_playlist:
        # 全クリアせずに一個上を取ってくる
        sp.playlist_add_items(playlist_id=GetPlaylistUri(PlaylistName), items=[uris_history[0]], position=[0])
        message_add = 'My Histroy was updated!!'
    else:
        print('the playlists are the same')
    return message_add

def LimitSongsinPlaylist(sp, PlaylistName, count, uris_history):
    message_limit = f'Number of the songs in the playlist {count}'
    if count >= 100:
        #count処理
        sp.playlist_remove_specific_occurrences_of_items(playlist_id=GetPlaylistUri(PlaylistName), items=[{'uri':uris_history[-1], 'positions':[100]}])
        message_limit = 'My old history song was deleted from the playlist'
    return message_limit

@tasks.task(tasks.CronTrigger('0 7 * * *'), auto_start=True) # UTC TIME ZONE 0 7 * * *
async def TopTracksPlaylist():
    # sp loopで複数処理できるか調べる

    for username in usernames:
        info = user_info[username]
        client_id = info['client_id']
        client_secret = info['client_secret']

        cache_handler = spotipy.cache_handler.CacheFileHandler(username=username)
        sp_auth = spotipy.oauth2.SpotifyOAuth(client_id=client_id,
                                    client_secret=client_secret,
                                    redirect_uri=redirect_url,
                                    scope=scope,
                                    cache_handler=cache_handler,
                                    show_dialog=True)
        sp = spotipy.Spotify(auth_manager=sp_auth)

        print(username)
        display_name = sp.me()['display_name']

        PlaylistNames = ['short_term', 'medium_term', 'long_term']
        PlaylistDict = {}
        dict_messages = ''
        for PlaylistName in PlaylistNames:
            MakingPlaylist(sp, PlaylistName)
            load_uris = GetSongsUriinPlaylist(sp, PlaylistName)
            message = AddTopSongs(sp, PlaylistName, load_uris, PlaylistDict)
        print('all done!!!')
        # organize message
        for key, value in PlaylistDict.items():
            dict_message = f'{key} : {value}'
            dict_messages += f'{dict_message}\n'
        print(dict_messages)
        await bot.rest.create_message(os.environ['NotificationChatRoom'], f'***> {display_name}\n{dict_messages}***')

try:
  bot.run(
      status=hikari.Status.ONLINE,
      activity=hikari.Activity(
          name="",
          type=hikari.ActivityType.COMPETING,
      ),
  )
except:
  os.system("kill 1")