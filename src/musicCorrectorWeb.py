from mutagen.mp4 import MP4 as mutagenMP4
import glob
import acoustid
from unidecode import unidecode
import discogs_client as discogsclient
import requests
import jellyfish
import json
import re
import sys
import html
from collections import Counter
import urllib
import musicbrainzngs
import os
from shutil import copyfile
import hashlib
import MySQLdb as mysqldb
import time
import datetime


class Globals:
  clients = []
  pass

class Translator:
  def __init__(self, file_type = 'mp4'):
    if file_type == 'mp4':
      self.table = {'SongTitle': '\xa9nam', 'SongTitleSortOrder': 'sonm', 'ArtistName': '\xa9ART', 'ArtistNameSortOrder': 'soar',
      'AlbumName': '\xa9alb', 'AlbumNameSortOrder': 'soal', 'AlbumArtists': 'aART', 'AlbumArtistsSortOrder': 'soaa',
      'AlbumYear': '\xa9day', 'Comments': '\xa9cmt', 'AlbumGenres': '\xa9gen', 'SongLyrics': '\xa9lyr',
       'TrackPosition': 'trkn[0][0]', 'AlbumTotalTracks': 'trkn[0][1]'}

  def translate(self, keys):
    values = []
    for key in keys:
      values.append(self.table[key])
    return values


# TODO: Add support for MP3
class MP4(mutagenMP4):
  def __init__(self, filename):
    super(MP4, self).__init__(filename)
    self.artisttag = str(self.tags['\xa9ART']).replace('[', '').replace(']', '').replace('\'', '')
    self.titletag = str(self.tags['\xa9nam']).replace('[', '').replace(']', '').replace('\'', '')
    self.filename = filename
    with open(filename, 'rb') as f:
      data = f.read()
      self.MD5 = hashlib.md5(data).hexdigest()

  def fingerprint(self, fingerprintlib, apitoken, minscore=0, trusttags=True):
    commonmatches = []
    # TODO: Add additional fingerprinting library
    if fingerprintlib == 'AcousticId':
      acousticidmatches = AcousticIdMatches()
      for score, recordingid, title, artist in acoustid.match(apitoken, self.filename):
        if score and score > minscore and title and artist:
          artist = re.sub(r";.*$", "", str(artist))
          AcousticMatch(str(title), artist)
          acousticidmatches.append(AcousticMatch(str(title), artist))
        Logger.log('\tScore: ' + str(score) +
                   '\tTitle: ' + str(title) +
                   '\tArtist: ' + str(artist) +
                   '\n')
      if trusttags:
        acousticidmatches.append(AcousticMatch(self.titletag, self.artisttag))
      commonmatches = acousticidmatches.most_common()
    return commonmatches

  def set_info_from_db(self, columnvalues):
    for columnvalue in columnvalues:
      try:
        Globals.translator.table[columnvalue[0]]
      except:
        columnvalues.remove(columnvalue)

    columns = []
    for columnvalue in columnvalues:
      columns.append(columnvalue[0])
    tagnames = Globals.translator.translate(columns)
    i = 0
    for value in columnvalues:
      if 'trkn' not in tagnames[i]:
        self.tags[tagnames[i]] = str(value[1])
      elif '[0][0]' in tagnames[i]:
        intposition = value[1]
      elif '[0][1]' in tagnames[i]:
        totaltracks = value[1]
        self.tags['trkn'] = [(intposition, totaltracks)]
      i += 1
    self.save()

  def set_info(self, selectedrelease):
    release = selectedrelease.release
    track = selectedrelease.track
    self.tags['\xa9ART'] = release.artist  # artisttag
    self.tags['soar'] = release.artist  # artist sort order
    self.tags['\xa9nam'] = track.title  # titletag
    self.tags['sonm'] = track.title  # title sort order
    self.tags['\xa9alb'] = release.title  # albumtag
    self.tags['soal'] = release.title  # album sort order
    artists = ''
    for artist in release.artists:
      artist = Artist(artist)
      artists += str(artist.fixedname)+','
    artists = artists[0:len(artists)-1]
    self.tags['aART'] = artists  # albumartisttag
    self.tags['soaa'] = artists  # album artist sort order
    self.tags['\xa9day'] = str(release.year)  # yeartag
    self.tags['\xa9cmt'] = 'Corrected_Web'  # commenttag
    genres = ''
    for genre in release.genres:
      genres += str(genre)+','
    genres = genres[0:len(genres) - 1]
    self.tags['\xa9gen'] = genres  # genretag
    self.tags['\xa9lyr'] = ''  # lyricstag
    self.tags['trkn'] = [(track.intposition, release.totaltracks)]  # tracknumtag
    self.save()

  def get_info(self):
    columns = ['SongTitle', 'SongTitleSortOrder', 'ArtistName', 'ArtistNameSortOrder', 'AlbumName', 'AlbumNameSortOrder',
               'AlbumArtists', 'AlbumArtistsSortOrder', 'AlbumYear', 'Comments', 'AlbumGenres', 'SongLyrics',
               'TrackPosition', 'AlbumTotalTracks']
    tagnames = Globals.translator.translate(columns)
    tup_list = []
    i = 0
    for column in columns:
      if 'trkn' not in tagnames[i]:
        tmp_tup = (column, self.tags[tagnames[i]])
      elif '[0][0]' in tagnames[i]:
        tagname = 'trkn'
        tmp_tup = (column, self.tags[tagname][0][0])
      elif '[0][1]' in tagnames[i]:
        tagname = 'trkn'
        tmp_tup = (column, self.tags[tagname][0][1])
      tup_list.append(tmp_tup)
      i += 1
    md5_tup = ('MD5', self.MD5)
    return tup_list + [md5_tup]


class Client(discogsclient.Client):
  def __init__(self, clienttype, appname, version, apitoken, apiurl):
    # TODO: Add another music database client
    if clienttype == 'Discogs':
      super(Client, self).__init__(appname + '/' + version, user_token=apitoken)
    elif clienttype == 'Musicbrainz':
      musicbrainzngs.set_useragent(appname, version)
    self.apitoken = apitoken
    self.type = clienttype
    self.apiurl = apiurl


class Track:
  def __init__(self, track):
    self.duration = track.duration
    self.position = track.position
    self.title = track.title
    self.artists = track.artists
    self.credits = track.credits

  def set_intposition(self, intposition):
    self.intposition = intposition


class Artist:
  def __init__(self, artist):    
    self.id = artist.id
    self.name = artist.name
    self.fixedname = self.fix_artist(self.name)
    self.real_name = artist.real_name
    self.images = artist.images
    self.profile = artist.profile
    self.data_quality = artist.data_quality
    self.name_variations = artist.name_variations
    self.url = artist.url
    self.urls = artist.urls
    self.aliases = artist.aliases
    self.members = artist.members
    self.groups = artist.groups

  def set_fixedname(self, fixedname):
    self.fixedname = fixedname

  def fix_artist(self, artist):
    # TODO: If artist_name (\d)
    return re.sub(r"\s+\([0-9]+\)\s*$", "", artist)


class AcousticMatch:
  title = ''
  artist = ''

  def __init__(self, title='', artist=''):
    self.title = title
    self.artist = artist

  def __str__(self):
    return self.artist + ' - ' + self.title

  def select_release(self):
    url = self.build_url()
    return self.process_request(url)

  def build_url(self):
    encodedtitle = urllib.parse.quote_plus(unidecode(self.title))
    encodedartist = urllib.parse.quote_plus(unidecode(self.artist))
    if Globals.currentclient.type == 'Discogs':
      urlparams = 'search?type=release&q=track:"' + encodedtitle + '"&artist="' + encodedartist \
                  + '"&sort=year&sort_order=asc&token=' + Globals.currentclient.apitoken
      url = Globals.currentclient.apiurl + urlparams
    return url

  def process_request(self, url):
    r = requests.get(url)
    if r.status_code == 200:
      jsonobj = json.loads(r.text)
    Logger.log(url + '\nStatus Code: ' + str(r.status_code))

    oldestalbum = None
    oldestep = None
    oldestsingle = None
    pagecounter = 1
    while r and r.status_code == 200 and pagecounter <= jsonobj['pagination']['pages']:
      for release in jsonobj['results']:
        release = self.main_release(release)
        Logger.log('\t' + str(release))
        Logger.log('\t' + str(release.formats))
        if self.skip_release(release):
          Logger.log('Skipping...')
          continue
        trackcounter = 0
        for track in release.tracklist:
          trackcounter += 1
          track = Track(track)
          track.set_intposition(trackcounter)
          Logger.log('\t\t' + str(jellyfish.jaro_winkler(track.title.lower(), self.title.lower())))
          if jellyfish.jaro_winkler(track.title.lower(), self.title.lower()) > Globals.MIN_TRACK_SIMILARITY:
            #Logger.log('\t\t----------------->' + str(track) + '<-----------------')
            Logger.log('\t\tFOUND TRACK: ' + str(track))
            tmpoldestalbum, tmpoldestep, tmpoldestsingle = self.album_ep_or_single(release, track)
            if oldestalbum is None:
              oldestalbum = tmpoldestalbum
            if oldestep is None:
              oldestep = tmpoldestep
            if oldestsingle is None:
              oldestsingle = tmpoldestsingle
            if oldestalbum or oldestep or oldestsingle:
              break
          else:
            Logger.log('\t\t' + str(track))

        if oldestalbum:
          break

      if oldestalbum:
        return oldestalbum

      pagecounter += 1
      if int(jsonobj['pagination']['pages']) > 1 and \
          pagecounter <= int(jsonobj['pagination']['pages']) and \
          'next' in jsonobj['pagination']['urls']:
        url = jsonobj['pagination']['urls']['next'] + '&token=' + Globals.currentclient.apitoken
        Logger.log(url)
        r = requests.get(url)
        jsonobj = json.loads(r.text)
      else:
        r = None
      if r is None or r.status_code != 200:
        if oldestep:
          returnrelease = oldestep
        elif oldestsingle:
          returnrelease = oldestsingle
        else:
          returnrelease = None
        return returnrelease

  def main_release(self, release):
    if release['type'] == "master":
      release = Globals.currentclient.release(str(release['main_release']))
    else:
      release = Globals.currentclient.release(str(release['id']))
    return release

  def skip_release(self, release):
    formatsstring = str(release.formats)
    return (('Compilation' in formatsstring) or (
              'Transcription' in formatsstring) or (
              'Promo' in formatsstring) or (
              'Reissue' in formatsstring) or (
              'DVD' in formatsstring) or (
              'Unofficial Release' in formatsstring) or (
              'Live' in str(release.title)))

  def album_ep_or_single(self, release, track):
    oldestalbum, oldestep, oldestsingle = (None, None, None)
    if 'Album' in str(release.formats):
      oldestalbum = AlbumTrackCombiner(self.artist, release, track)
    elif 'EP' in str(release.formats):
      oldestep = AlbumTrackCombiner(self.artist, release, track)
    elif 'Single' in str(release.formats):
      oldestsingle = AlbumTrackCombiner(self.artist, release, track)
    return oldestalbum, oldestep, oldestsingle


class AcousticIdMatches(list):
  separator = ':--:'

  def append(self, p_object):
    super(AcousticIdMatches, self).append(p_object.title+self.separator+p_object.artist)

  def most_common(self):
    matcheslist = []
    if len(self) > 1:
      counter = Counter(self)
      #Logger.log('*********************************************************')
      Logger.log(counter.most_common())
      #Logger.log('*********************************************************')
      freq_most_common = 0
      tuple_counter = 0
      for commontuple in counter.most_common():
        tuple_counter += 1
        (titleartist, freq) = commontuple
        if tuple_counter == 1:
          freq_most_common = freq
        if freq < freq_most_common:
          break
        title, artist = titleartist.split(self.separator, 1)
        append = True
        for match in matcheslist:
          if title.lower() == match.title.lower() and artist.lower() == match.artist.lower():
            append = False
            break
        if append:
          matcheslist.append(AcousticMatch(title, artist))

    elif len(self) == 1:
      title, artist = self[0].split(self.separator, 1)
      matcheslist.append(AcousticMatch(title, artist))
    return matcheslist


class AlbumTrackCombiner:

  def __init__(self, artist, release, track):
    self.release = release
    self.release.artist = self.fix_artist(artist)
    i = 0
    for artist in self.release.artists:
      artist = Artist(artist)
      Logger.log('Fixing: '+artist.name+' to '+artist.fixedname)
      i+=1
    self.track = track
    if self.release.images:
      imageurls = ''
      for image in self.release.images:
        imageurls += image['resource_url']+','
      imageurls = imageurls[0:len(imageurls)-1]
      self.release.imageurls = imageurls
    else:
      self.release.imageurls = 'Images not available'
    self.release.totaltracks = len(self.release.tracklist)

  def convert_position_2_int(self, position):
    try:
      intposition = int(str(position))
    except:
      if re.search(r"^[a-z][0-9]$", str(position).lower()):
        firstint = ord(str(position).lower()[0])-ord('a')
        secondint = int(str(position)[1])
        intposition = firstint*10+secondint
      else:
        intposition = 0
    return intposition

  def fix_artist(self, artist):
    # TODO: If artist_name (\d)
    return re.sub(r"\s+\([0-9]+\)\s*$", "", artist)

  def __str__(self):
    return self.release.title + '\t' + \
           self.release.artist + '\t' + \
           str(self.release.id) + '\t' + \
           str(self.release.year) + '\t' + \
           self.release.country + '\t' + \
           str(self.release.formats) + '\t' + \
           str(self.release.artists) + '\t' + \
           str(self.release.genres) + '\t' + \
           self.release.imageurls + '\n' + \
           self.track.title + '\t' + \
           self.track.position + '\t' + \
           str(self.track.intposition) + \
           str(self.release.totaltracks) + '\n'

  def get_info(self):
    title_tup = ('SongTitle', self.track.title)
    artist_tup = ('ArtistName', self.release.artist)
    album_tup = ('AlbumName', self.release.title)
    discogs_id = ('AlbumDiscogsID', self.release.id)
    artists = ''
    for artist in self.release.artists:
      artist = Artist(artist)
      artists += str(artist.fixedname)+','
    artists = artists[0:len(artists)-1]
    album_artists_tup = ('AlbumArtists', artists)
    year_tup = ('AlbumYear', self.release.year)
    country_tup = ('AlbumCountry', str(self.release.country))
    status_tup = ('AlbumStatus', self.release.status)
    genres = ''
    for genre in self.release.genres:
      genres += str(genre)+','
    genres = genres[0:len(genres)-1]
    genres_tup = ('AlbumGenres', genres)
    formats = ''
    for format in self.release.formats:
      formats += str(format)+','
    formats = formats[0:len(formats)-1]
    formats_tup = ('AlbumFormats', formats)
    image_urls_tup = ('AlbumImageUrls', self.release.imageurls)
    track_pos_tup = ('TrackPosition', self.track.position)
    track_int_pos_tup = ('TrackIntPosition', self.track.intposition)
    album_tracks_tup = ('AlbumTotalTracks', self.release.totaltracks)
    return [title_tup, artist_tup, discogs_id, album_tup, album_artists_tup, year_tup, country_tup, status_tup,
            genres_tup, formats_tup, image_urls_tup, track_int_pos_tup, track_pos_tup, album_tracks_tup]


class Logger:
  @classmethod
  def __init__(cls, logpath):
    cls.f = open(logpath, 'a')

  @classmethod
  def log(cls, string2log):
    try:
      ts = time.time()
      st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
      string2log = unidecode(str(string2log)).rstrip()
      #string_html = html.escape(string2log).replace('\n', '<br>').replace(' ', '&nbsp;')\
      #    .replace('\t', '&nbsp;&nbsp;&nbsp;')
      #print(st + ' >>> ' + string_html + '<br>')
      cls.f.write(st + ' >>> ' + string2log + '\n')
    except Exception as e:
      #print('Exception!! '+str(e) + '<br>')
      cls.f.write('Exception!! '+str(e) + '\n')

  @classmethod
  def close(cls):
    cls.f.close()


class Database:
  @classmethod
  def __init__(cls, host, user, passwd, dbname):
    cls.dbinstance = mysqldb.connect(host=host, user=user, passwd=passwd, db=dbname)
    cls.dbinstance.autocommit(True)
    cls.c = cls.dbinstance.cursor()
    cls.dbinstance.set_character_set('utf8')
    cls.c.execute('SET NAMES utf8;')
    cls.c.execute('SET CHARACTER SET utf8;')
    cls.c.execute('SET character_set_connection=utf8;')

  @classmethod
  def select(cls, column, tablename, condition):
    Logger.log('SELECT '+column+' from '+tablename+' where '+condition+';')
    cls.c.execute('SELECT '+column+' from '+tablename+' where '+condition+';')
    fetch_all = cls.c.fetchall()
    if fetch_all:
      fetch_all = fetch_all[0]
      Logger.log(fetch_all)
    return fetch_all

  @classmethod
  def select_with_columns(cls, column, tablename, condition):
    Logger.log('SELECT '+column+' from '+tablename+' where '+condition+';')
    cls.c.execute('SELECT '+column+' from '+tablename+' where '+condition+';')

    columns = []
    for field in cls.c.description:
      columns.append(field[0])

    return_fetch = []
    i = 0
    fetch_all = cls.c.fetchall()
    fetch_all = fetch_all[0]
    for fetch in fetch_all:
      tmp_tup = (columns[i], fetch)
      return_fetch.append(tmp_tup)
      i += 1
      if i % len(columns) == 0:
        i = 0
    Logger.log(return_fetch)
    return return_fetch

  @classmethod
  def insert(cls, tablename, values):
    columns = ''
    columns_values = ''
    for value_tup in values:
      columnname, value = value_tup
      columns += columnname + ', '
      if isinstance(value, str):
        columns_values += '\'' + value.replace('\'', '\'\'') + '\'' + ', '
      else:
        columns_values += str(value).replace('\'', '\'\'') + ', '
    columns = columns[0:len(columns)-2]
    columns_values = columns_values[0:len(columns_values)-2]
    Logger.log('INSERT INTO '+tablename+' ('+columns+') VALUES ('+columns_values+');')
    cls.c.execute('INSERT INTO '+tablename+' ('+columns+') VALUES ('+columns_values+');')

  @classmethod
  def update(cls, tablename, fieldvalues, condition):
    setstring = ''
    for fieldvalue in fieldvalues:
      field, value = fieldvalue
      if isinstance(value, str):
        setstring += field + ' = ' + '\'' + value.replace('\'', '\'\'') + '\'' + ', '
      else:
        setstring += field + ' = ' + str(value).replace('\'', '\'\'') + ', '
    setstring = setstring[0:len(setstring)-2]
    Logger.log('UPDATE '+tablename+' SET '+setstring+' WHERE '+condition+';')
    cls.c.execute('UPDATE '+tablename+' SET '+setstring+' WHERE '+condition+';')

  @classmethod
  def delete(cls, tablename, condition):
    Logger.log('DELETE FROM '+tablename+' WHERE '+condition+';')
    cls.c.execute('DELETE FROM '+tablename+' WHERE '+condition+';')

  @classmethod
  def close(cls):
    cls.c.close()
    cls.dbinstance.close()

class Json:
  def __new__(cls, dbinfo):
    return json.dumps(dbinfo)

def copy2newdir(filename):
  basename = os.path.basename(filename)
  new_filename = Globals.MUSICNEWDIR+'/'+basename
  copyfile(filename, new_filename)
  # TODO: If new_filename exists add distinct string and copy
  return new_filename

def getmd5fromfile(filename):
  with open(filename, 'rb') as f:
    data = f.read()
    return hashlib.md5(data).hexdigest()

def cleanup():
  Database.close()
  Logger.close()
  pass


def main():
  if len(sys.argv) < 2 or len(sys.argv) > 3:
    print('Incorrect number of arguments')
    sys.exit(1)
  filename = sys.argv[1]
  if not os.path.isfile('/var/www/html/audio-fingerprint-tagger/uploads/'+filename):
    sys.exit(2)
  else:
    filename = '/var/www/html/audio-fingerprint-tagger/uploads/'+filename
  try:
    Globals.LOGFILE = '/var/www/html/audio-fingerprint-tagger/logs/'+sys.argv[2]
  except:
    Globals.LOGFILE = '/var/www/html/audio-fingerprint-tagger/logs/musicCorrectorWeb.log'
  Globals.APPNAME = 'musicCorrectorWeb'
  Globals.VERSION = '0.0.1'
  Globals.DISCOGS_API_TOKEN = 'TpOVGnsdTpMrkPVaRhUqXZXUrapnKmEXyQOKukJf'
  Globals.ACOUSTICID_API_KEY = 'hqTbuf1Zny'
  Globals.MUSICDIR = '/var/www/html/audio-fingerprint-tagger/uploads'
  Globals.MUSICNEWDIR = '/var/www/html/audio-fingerprint-tagger/corrected'
  Globals.MIN_FINGERPRINT_SCORE = .70
  Globals.MIN_TRACK_SIMILARITY = .80
  # TODO: Get values from config file
  Logger(Globals.LOGFILE)
  Database(host="localhost", user="ymolinar", passwd="Yams31416Y", dbname="musiccorrectordb")

  Globals.clients.append(Client(clienttype='Discogs', appname=Globals.APPNAME, version=Globals.VERSION,
             apitoken=Globals.DISCOGS_API_TOKEN, apiurl='https://api.discogs.com/database/'))
  Globals.discogsclient = Globals.clients[0]
  Globals.currentclient = Globals.discogsclient
  Globals.translator = Translator()
  # TODO: Build scheduler and run parallel scripts
  # TODO: Add support for extra discogs tokens and extra servers (distributed)
  # TODO: Divide single file into modules
  md5 = getmd5fromfile(filename)
  songexists = Database.select('SongID', 'songtags', 'MD5=\'' + md5 + '\'')
  # TODO: Add logic to skip empty db info
  if songexists:
    new_filename = copy2newdir(filename)
    mp4file = MP4(new_filename)
    songdata = Database.select_with_columns('*', 'songtags', 'MD5=\'' + md5 + '\'')
    mp4file.set_info_from_db(songdata)
    jsonfile = Json(songdata)
    print(jsonfile)
    return 0

  new_filename = copy2newdir(filename)
  mp4file = MP4(new_filename)

  #Logger.log('------------------------------------------------------------------------------')
  Logger.log(unidecode(filename) + '\n')
  Logger.log(unidecode(new_filename) + '\n')
  Logger.log(mp4file.artisttag + ' - ' + mp4file.titletag + '\n')
  #Logger.log('------------------------------------------------------------------------------')

  commonmatches = mp4file.fingerprint(fingerprintlib='AcousticId', apitoken=Globals.ACOUSTICID_API_KEY,
                                      minscore=Globals.MIN_FINGERPRINT_SCORE)

  if len(commonmatches) > 0:
    selectedrelease = None
    for commonmatch in commonmatches:
      selectedrelease = commonmatch.select_release()
      if selectedrelease:
        break
    #Logger.log('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    if selectedrelease:
      Logger.log(selectedrelease)
      # TODO: Get lyrics
      # TODO: Add image to file
      mp4file.set_info(selectedrelease)
      mp4md5 = mp4file.MD5
      Database.insert('songtags', mp4file.get_info())
      songid = Database.select('SongID', 'songtags', 'MD5=\''+mp4md5+'\'')[0]
      songid_tup = ('SongID', songid)
      selectedreleaseinfo = selectedrelease.get_info()
      selectedreleaseinfo.append(songid_tup)
      Database.insert('discogsdbinfo', selectedreleaseinfo)
      jsonfile = Json(selectedreleaseinfo)
      print(jsonfile)
    else:
      # TODO: Set md5 to db to show file could not be fixed
      Logger.log('Could not find any suitable release')
      print(json.dumps('Could not find any suitable release'))
    #Logger.log('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    return 0

if __name__ == "__main__":
    try:
        main()
        cleanup()
    except KeyboardInterrupt:
        Logger.log('Interrupt! Cleanup')
        cleanup()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

