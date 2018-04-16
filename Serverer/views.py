# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from os import walk

from django.views.decorators.csrf import csrf_exempt
import json
from tinytag import TinyTag
from MusicServer import settings
from models import *


# Create your views here.


def home(request):
    return render(request, 'Home.html')


def cmpx(x1, x2):
    return (x1 > x2) - (x1 < x2)


def cmpc(c1, c2):
    chrs = [u"àảãáạăằẳẵắặâầẩẫấậ",
            u"đ",
            u"èẻẽéẹêềểễếệ",
            u"ìỉĩíị",
            u"òỏõóọôồổỗốộơờởỡớợ",
            u"ùủũúụưừửữứự",
            u"ỳỷỹýỵ"]
    kqua = u"adeiouy"

    def bodau(a):
        a += u""
        for i, v in enumerate(chrs):
            if a in v:
                return kqua[i]
        return a

    def pos(a):
        for i, v in enumerate(chrs):
            if a in v:
                return i
        return -1

    c1 = c1.lower()
    c2 = c2.lower()
    if c1 == c2:
        return 0
    p1 = pos(c1)
    p2 = pos(c2)
    if p1 == -1 and p2 == -1:
        return cmpx(c1, c2)
    elif p1 != -1 and p2 != -1:
        if p1 == p2:
            cs = chrs[p1]
            return cmpx(cs.find(c1), cs.find(c2))
        else:
            return cmpx(p1, p2)
    elif p1 != -1 and p2 == -1:
        if bodau(c1) >= c2:
            return 1
        else:
            return -1
    else:  # p1 == -1 and p2 != -1
        if c1 > bodau(c2):
            return 1
        else:
            return -1


def cmps(s1, s2):
    for i in range(0, min(len(s1), len(s2))):
        if s1[i] != s2[i]:
            return cmpc(s1[i], s2[i])
    return cmpx(len(s1), len(s2))


def cmp_song(s1, s2):
    return cmps(s1.title, s2.title)


def getinfo(request):
    x = {}
    pgsize = int(request.GET.get('pgsize', 20))
    pg = int(request.GET.get('pg', 0))

    song_list = list(Song.objects.all())
    song_list.sort(cmp_song)
    song_list = song_list[pg * pgsize:pg * pgsize + pgsize]
    data = []
    for song in song_list:
        duration = song.duration
        item = {'name': song.title.title(),
                'artist': song.artist,
                'duration': '{:02d}:{:02d}'.format(duration / 60, duration % 60),
                'id': song.id}
        data.append(item)
    x['data'] = data
    x['count'] = len(song_list)
    x['total'] = Song.objects.count()
    x['page'] = pg
    return JsonResponse(x)


word_set = []
cur_pos = 0


def check_word(cur):
    global word_set, cur_pos
    res = [False, False]
    while cur > word_set[cur_pos]:
        cur_pos += 1
    if word_set[cur_pos].startswith(cur):
        res[0] = True
        if word_set[cur_pos] == cur:
            res[1] = True
    return res


def anagram(chrs, cur=''):
    res = []
    if len(chrs) == 1:
        cur = cur + chrs[0]
        x = check_word(cur)
        if x[1]:
            res.append(cur)
    else:
        for ci, cv in enumerate(chrs):
            cur += cv
            x = check_word(cur)
            if x[1]:
                res.append(cur)
            if x[0]:
                res.extend(anagram(chrs[:ci] + chrs[ci + 1:], cur))
            cur = cur[:-1]
    return res


@csrf_exempt
def wordgen(request):
    global word_set, cur_pos
    re = {}
    bd = json.loads(request.body)
    try:
        chrset = str(bd['chrset']).lower()
    except:
        chrset = ''

    chrset = ''.join(sorted(chrset))
    inp = open(settings.BASE_DIR + '/Serverer/Resources/word/word.wd')
    word_set = []
    cur_pos = 0
    for ln in inp:
        word_set.append(ln.strip())
    inp.close()
    reswd = anagram(chrset)
    reswd = set(reswd)
    reswd = filter(lambda x: len(x) > 2, reswd)
    type_arr = []
    type_count = 0
    for i in range(3, 10):
        wi = sorted(filter(lambda x: len(x) == i, reswd))
        wil = len(wi)
        if wil > 0:
            type_count += 1
            type_arr.append(i)
            re['len' + str(i)] = {
                'count': str(wil),
                'words': wi
            }
    re['count'] = type_count
    re['types'] = type_arr
    return JsonResponse(re)


def worgenfront(request):
    return render(request, 'wordGen.html')


def getmp3(request):
    song_id = int(request.GET.get('id', 1))
    song = Song.objects.get(id=song_id)
    fs = FileSystemStorage()
    with fs.open(song.path) as mp3:
        response = HttpResponse(mp3,
                                content_type='audio/mpeg')
        return response


def refreshdb():
    res = {'status': 'ok'}
    count = 0
    Song.objects.all().delete()
    for root, dirs, files in walk(settings.BASE_DIR + '/Serverer/Resources/Music'):
        for f in files:
            count += 1
            path = root + '/' + f
            song_file = TinyTag.get(path)
            song = Song(title=song_file.title, artist=song_file.artist, duration=int(song_file.duration), path=path)
            song.save()
    res['song'] = count


def rdb(request):
    refreshdb()
    return HttpResponse("OK")
