

#! /usr/bin/env python3

"""
Usage:
    empupload.py prepare <media>
       [--screens=<screens> --torrents=<torrents> --txtlocation=<txtlocation> --trackerurl=<trackerurl> ]
       [--config=<configpath]
"""


from bs4 import BeautifulSoup
import http.cookiejar
import requests
import subprocess
from docopt import docopt
from pathlib import Path
import json
import os
import pickle
import subprocess
import imageio
from pygifsicle import gifsicle
import shutil
import math
import configparser
config = configparser.ConfigParser()
import shlex
import json
import pprint


def getBasedName(path):
    basename=subprocess.check_output(['basename',path])

    basename=basename.decode('utf-8')
    if Path(path).is_dir():
        basename=basename[0:-1]
        return basename
    else:
        basename=(os.path.splitext(basename))

# function to find the resolution of the input video file
def findVideoMetadata(pathToInputVideo):
    cmd = "ffprobe -v quiet -print_format json -show_streams"
    args = shlex.split(cmd)
    args.append(pathToInputVideo)
    # run the ffprobe process, decode stdout into utf-8 & convert to JSON
    ffprobeOutput = subprocess.check_output(args).decode('utf-8')
    ffprobeOutput = json.loads(ffprobeOutput)
    duration = ffprobeOutput['streams'][1]['duration']
    width = ffprobeOutput['streams'][1]['coded_width']
    return duration,width




def createconfig(arguments,configpath):
        screens=None
        torrents=None
        txtlocation=None
        trackerurl=None

        if arguments.get('--config')!=None:
            configpath=arguments.get('--config')

        if os.path.isfile(configpath)==True:
            config.read(configpath)
            screens=config['Dirs']['screens']
            torrents=config['Dirs']['torrents']
            txtlocation=config['Dirs']['txtlocation']
            trackerurl=config['Dirs']['trackerurl']


        if arguments.get('--screens')!=None:
            screens=arguments.get('--screens')
        if arguments.get('--torrents')!=None:
            torrents=arguments.get('--torrents',torrents)
        if arguments.get('--txtlocation')!=None:
            txtlocation=arguments.get('--txtlocation',txtlocation)
        if arguments.get('--trackerurl')!=None:
            trackerurl=arguments.get('--trackerurl',trackerurl)
        #check variables
        if screens==None:
            print("--screens='where to save images?' is missing")
            quit()
        if torrents==None:
            print("--torrents='where to save torrents?' is missing")
            quit()
        if txtlocation==None:
            print("--txtlocation='upload txt location' is missing")
            quit()

        if trackerurl==None:
            print("--trackerurl='Please Enter  your tracker url'")
            quit()
        return[screens,torrents,txtlocation,trackerurl]


def fapping_upload(cover,img_path: str) -> str:
    """
    Uploads an image to fapping.sx and returns the image_id to access it
    Parameters
    ----------
    img_path: str
    the path of the image to be uploaded
    Returns
    -------
    str
    """
    with requests.Session() as s:
        # posts the image as a binary file with the upload form
        r = s.post('https://fapping.empornium.sx/upload.php',
                   files=dict(ImageUp=open(img_path, 'rb')))
        if r.status_code == 200:
            print(r.status_code)
            image=json.loads(r.text)['image_id_public']
            image="https://fapping.empornium.sx/image/" +image
            image=requests.get(image)
            soup = BeautifulSoup(image.text, 'html.parser')
            soup= soup.find('div',{'class' :'image-tools-section thumb_plus_link'})
            inputitem=(soup.find('div',{'class' :'input-item'}).descendants)
            #get bbcode for upload, thumbnails
            link=list(inputitem)
            if(cover==0):
                link=str(link[3]).split()[3][7:-3]
            else:
                link=str(link[3]).split()[3].split(']')[2][0:-5]
                link=link.replace('.th','')

            return link

        else:
            print('Error occurred during image upload')
            return None
def createimages(path,dir):
    imgstring=""
    count=0
    cover=0
    print("Creating thumbs")
    if Path(path).is_dir():
        os.chdir(path)
        t=subprocess.check_output(['fd','--absolute-path','-e','.mp4','-e','.flv','-e','.mkv','-e','.m4v','-e','.mov'])
        t=t.decode('utf-8')
        os.mkdir(dir)
        os.chdir(dir)
#Loop files in Directory
        for line in t.splitlines():
            count=count+1
            print("Video Number:" +str(count))
            subprocess.call(['vcsi',line,'-g','3x3','-o',dir,'-w','2880','--quality','92'])


## Files not in Dir

    else:
        os.mkdir(dir)
        os.chdir(dir)
        subprocess.call(['vcsi',path,'-g','3x3','-o',dir,'-w','2880','--quality','92'])
        subprocess.call(['vcs','-h','960','-n','9','-c','3','-A','-j',path])
#upload image
    #for i,line in enumerate(t):
    print("Uploading Max 100 Images")
    for i, image in enumerate(os.listdir(dir)):
            if i>100:
                print("Max images reached")
                break
            image=dir+image
            upload=fapping_upload(cover,image)
            if upload!=None:
                imgstring=imgstring+upload
#zip or just move images to directory being uplaoded to EMP
    print("Moving Images")
    if(count>=100):
        subprocess.call(['7z','a',path+ '/'+ 'thumbnail.zip',dir])
    elif(count>=10):
        photos=path+'/thumbs/'
        photos=photos.replace('//', '/')
        print(photos)
        if os.path.isdir(photos):
            shutil.rmtree(photos)
        shutil.copytree(dir, photos)
    #finalize image string
    imgstring='[spoiler=Thumbs]'+imgstring+'[/spoiler]'
    return imgstring

def createDescription(imagelist,basename,txtlocation):
    txt=txtlocation + basename+ '.txt'
    desc=""
    with open(txt) as x:
        t=x.readlines()
        for i,line in enumerate(t):
            if i==0:
                title=line
            if i==1:
                tags=line
            if i>1:
                desc=desc+line
    desc=desc+'\n'+'\n' +imagelist
    return[title,tags,desc]



def createcovergif(path,dir,basename,txtlocation):
  print("Finding Largest File and Creating gif")
  max=0
  maxfile=path
  if Path(path).is_dir():
      os.chdir(path)
      t=subprocess.check_output(['fd','--absolute-path','-e','.mp4','-e','.flv','-e','.mkv'])
      t=t.decode('utf-8')
      if len(t)==0:
        return print("No Video Files for gif creation")
      for file in t.splitlines():
          temp=os.path.getsize(file)
          if(temp>max):
              max=temp
              maxfile=file
  outputPath = txtlocation +basename+'.gif'
  numframes=0
  print(f'Convert {maxfile} \n  {outputPath}')

  reader = imageio.get_reader(maxfile)
  fps = reader.get_meta_data()['fps']
  fps=fps/2
  duration=findVideoMetadata(maxfile)[0]
  width = int(findVideoMetadata(maxfile)[1])
  ##find scale
  if width>=3000:
    scale="--scale=.15"
  elif width>=1280:
    scale="--scale=.4"
  else:
      scale=-"--scale=1"
  startTime=float(duration)
  startTime=math.floor(startTime)*.75
  endTime=startTime+10

  writer = imageio.get_writer(outputPath, fps=fps)
  start=fps*startTime
  end=fps*endTime


  for i,frames in enumerate(reader):
    if i<start:
        continue
    if i%3!=0:
        continue
    if i>end:
        break
    # if(numframes%5!=0):
        # continue
    writer.append_data(frames)
    print(f'Quadro {frames} \n')
  print('Terminate!')
  writer.close()

  gifsicle(sources=[outputPath],destination=outputPath, optimize=True,options=[scale,"-O3"])
  cover=1
  try:
    upload=fapping_upload(cover,outputPath)

  except:
    print("Try a different Approved host gif too large")
    return
  return upload


def create_torrent(path,basename,trackerurl,torrents):
   print("Creating torrent")
   torrent=subprocess.check_output(['dottorrent','-p','-t',trackerurl,'-s','8M',path,torrents])
   output= torrents + basename+ '.torrent'
   return output


def create_upload_form(arguments):

#default variables
    path = arguments['<media>']
    basename=getBasedName(path)
    configpath=os.getenv("HOME")+'/.config/empupload.conf'
    config=createconfig(arguments,configpath)
    screens=config[0]
    torrents=config[1]
    txtlocation=config[2]
    trackerurl=config[3]


    output=txtlocation + '[EMPOUT]' +   basename+ '.txt'
    dir=screens + basename +'/'
    try:
        shutil.rmtree(dir)
    except:
        pass

    imagelist=createimages(path,dir)
    t=createDescription(imagelist,basename,txtlocation)
    title=t[0]
    tags=t[1]
    desc=t[2]
    torrent=create_torrent(path,basename,trackerurl,torrents)
    torrent = {'file_input': open(torrent,'rb')}
    cookies=cookie={"searchPanelState":"expanded","torrentDetailsState":"%5B%221%22%2C%221%22%2C%221%22%2C%221%22%2C%221%22%5D","tagsort":"%5B%22uses%22%2C%22desc%22%5D","torrentDetailsToolState":"expanded","SL_GWPT_Show_Hide_tmp":"1","SL_wptGlobTipTmp":"1","userPageState":"%5B%220%22%2C%221%22%2C%221%22%2C%220%22%2C%220%22%2C%220%22%2C%220%22%2C%220%22%2C%220%22%2C%221%22%2C%220%22%2C%221%22%2C%220%22%2C%221%22%2C%221%22%2C%221%22%2C%221%22%2C%221%22%5D,requestDetailsState:%5B%221%22%2C%221%22%2C%221%22%5D","sid":"%05%E6-%AFi%17%02%A6%CE%26I%CE5.%A4%E1%9E%C4%29L%17%3F%AEN%97%1E%7B%83%AE%13Qt%85%94%A9%D0%2C%9A%AD%FFE%10%CAZ%C4%92%E6Z%0C%BD%0F%97D%7E%FA%40sG%EC%9Fa3%12%F0","cid":"h%FF%1A%E0E%0AK%C2%EA%2A%1F%E7s%11%9AxB%2C%F5I%C4+%8A%DD%95%ED%15%8F%97%18%EF%8D%02c%FC%FC%A7o%60p%07%8A%C53%0EF%2F%AF6Q%FE%D8%B6%01%BA%3A7%FF%C4R%E0%2C%C1%D1"}
    empurl="https://www.empornium.me/upload.php"
    headers= {
  'Upgrade-Insecure-Requests': '1',
  'Origin': 'https://www.empornium.me',
  'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundarycPKQ6ZAmjTPUS1KM',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4404.132 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
}


    form = {'title' :  title,
            'taglist'  : 'bbw ssbbw pawg red.head onlyfans.com twerkin pale booty.shaking',
            'image' : createcovergif(path,dir,basename,txtlocation),
            'desc' : desc,
            'auth' :'q74iwm9qecdkjc93uw0r202ifxgqobn3',
            'category'  : 1,
            'anonymous' : 0,
            'submit' : 'true',
            'ignoredupes': 1,
            'autocomplete_toggle' : "on"


            }
    temp="/home/main/Tools/torrents/txt/Dirty/test.html"
    temp= open(temp,'w')
    upload=requests.post(url=empurl,cookies=cookies,files=torrent, data=form,headers=headers)
    temp.write(upload.text)
    print(upload.url)
    with open(output, 'w') as f:
        for key, value in form.items():
            f.write('%s:%s\n' % (key, value))

    #send temp paste
    output = {'file': open(output,'r')}
    post=requests.post(url="https://uguu.se/api.php?d=upload-tool",files=output)
    print(post.text)
    print("Torrent has been saved to:",torrent)

    shutil.rmtree(dir)






if __name__ == '__main__':
    arguments = docopt(__doc__)
    if arguments['prepare']:
        create_upload_form(arguments)
