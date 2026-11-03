#!/usr/bin/env python3
"""Plex year-in-review: extract aggregate metrics and render five PNG slides."""
import argparse, json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

SIZE=(1080,1350)
THEMES={
 "odyssey":dict(bg="#0c1921",panel="#162b34",accent="#f2b951",secondary="#86c7c4",fg="#f2f5f5"),
 "minimal":dict(bg="#141619",panel="#24282c",accent="#ededed",secondary="#a4b0b6",fg="#ffffff"),
}
def query(db,sql,params=()):
 return db.execute(sql,params).fetchall()
def extract(path,year):
 p=Path(path).resolve()
 if not p.is_file(): raise SystemExit("Database backup not found")
 # immutable=1 is for a fully checkpointed, standalone backup; never use with active Plex DB.
 db=sqlite3.connect("file:"+str(p)+"?mode=ro&immutable=1",uri=True)
 a=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp())
 b=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp())
 def scalar(sql,params=(a,b)): return query(db,sql,params)[0][0] or 0
 base="FROM metadata_item_views WHERE viewed_at>=? AND viewed_at<?"
 data={"year":year,
 "plays":scalar("SELECT COUNT(*) "+base),
 "viewers":scalar("SELECT COUNT(DISTINCT account_id) "+base),
 "unique_movies":scalar("SELECT COUNT(DISTINCT CASE WHEN metadata_type=1 THEN guid END) "+base),
 "unique_shows":scalar("SELECT COUNT(DISTINCT CASE WHEN metadata_type=4 THEN grandparent_title END) "+base),
 "hours":round(scalar("SELECT SUM(duration)/3600.0 FROM statistics_media WHERE timespan=1 AND at>=? AND at<?"),1),
 "tib":round(scalar("SELECT SUM(bytes)/1099511627776.0 FROM statistics_bandwidth WHERE timespan=1 AND at>=? AND at<?"),2),
 "library":{str(t):n for t,n in query(db,"SELECT metadata_type,COUNT(*) FROM metadata_items WHERE deleted_at IS NULL GROUP BY metadata_type")},
 "added":{str(t):n for t,n in query(db,"SELECT metadata_type,COUNT(*) FROM metadata_items WHERE deleted_at IS NULL AND added_at>=? AND added_at<? GROUP BY metadata_type",(a,b))},
 "through":datetime.fromtimestamp(scalar("SELECT MAX(viewed_at) "+base),timezone.utc).strftime("%b %d, %Y"),
 "library_size_label":None}
 for key,kind,field in [("top_movies",1,"title"),("top_shows",4,"grandparent_title")]:
  data[key]=[{"title":title or "Unknown","plays":n} for title,n in query(db,
  f"SELECT {field},COUNT(*) FROM metadata_item_views WHERE metadata_type=? AND viewed_at>=? AND viewed_at<? GROUP BY {field} ORDER BY COUNT(*) DESC,{field} LIMIT 3",(kind,a,b))]
 db.close()
 return data

def face(size,bold=False):
 names=(["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/System/Library/Fonts/Supplemental/Arial Bold.ttf","C:/Windows/Fonts/arialbd.ttf"] if bold else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/System/Library/Fonts/Supplemental/Arial.ttf","C:/Windows/Fonts/arial.ttf"])
 for name in names:
  if Path(name).exists():return ImageFont.truetype(name,size)
 return ImageFont.load_default()
def draw_text(d,x,y,s,color,size=36,bold=False,width=930):
 s=str(s)
 while size>16 and d.textbbox((0,0),s,font=face(size,bold))[2]>width:size-=2
 d.text((x,y),s,font=face(size,bold),fill=color)
def render(data,out,name,theme,cta,cta_text):
 p=THEMES[theme];out=Path(out);out.mkdir(parents=True,exist_ok=True)
 def blank():
  img=Image.new("RGB",SIZE,p["bg"]);d=ImageDraw.Draw(img)
  for x in range(0,1080,80):d.line((x,0,x,1350),fill="#203039",width=1)
  for y in range(0,1350,80):d.line((0,y,1080,y),fill="#203039",width=1)
  d.rectangle((0,0,1080,13),fill=p["accent"])
  return img,d
 def heading(d,t):
  draw_text(d,60,65,name.upper(),p["secondary"],34,True)
  draw_text(d,60,145,t,p["accent"],66,True)
  draw_text(d,60,240,f'{data["year"]} SO FAR / THROUGH {data["through"].upper()}',p["secondary"],23)
  d.line((60,295,1020,295),fill=p["secondary"],width=2)
 def card(d,y,label,value):
  d.rounded_rectangle((60,y,1020,y+155),radius=20,fill=p["panel"],outline=p["secondary"],width=2)
  draw_text(d,85,y+24,label.upper(),p["secondary"],24,True)
  draw_text(d,85,y+68,value,p["fg"],62,True)
 def page(n,fn):
  im,d=blank();fn(d);im.save(out/f"slide-{n}.png")
 def cover(d):
  draw_text(d,60,85,name.upper(),p["secondary"],38,True)
  draw_text(d,60,365,"REWIND",p["fg"],122,True)
  draw_text(d,60,515,str(data["year"]),p["accent"],165,True)
  draw_text(d,60,800,"YOUR YEAR IN STREAMING",p["secondary"],36,True)
  draw_text(d,60,1155,"A year powered by the community.",p["fg"],30)
 page(1,cover)
 def stats(d):
  heading(d,"BY THE NUMBERS")
  for i,(label,value) in enumerate([("Viewer accounts",f'{data["viewers"]:,}'),("Playback events",f'{data["plays"]:,}'),("Estimated streaming hours",f'{data["hours"]:,.0f}'),("Plex media traffic",f'{data["tib"]:.2f} TiB')]):card(d,342+i*189,label,value)
  draw_text(d,60,1190,"Playbacks are not necessarily completed watches.",p["secondary"],22)
 page(2,stats)
 def shows(d):
  heading(d,"MOST PLAYED")
  for title,y,key in [("TV SHOWS",346,"top_shows"),("MOVIES",792,"top_movies")]:
   draw_text(d,60,y,title,p["accent"],34,True)
   for i,item in enumerate(data[key]):
    yy=y+65+i*107
    d.rounded_rectangle((60,yy,1020,yy+96),radius=14,fill=p["panel"])
    draw_text(d,83,yy+25,f'{i+1}. {item["title"]}',p["fg"],30,True,760)
    draw_text(d,893,yy+25,item["plays"],p["accent"],30,True,100)
  draw_text(d,60,1240,"Ranked by play events, not completed watches.",p["secondary"],21)
 page(3,shows)
 def library(d):
  heading(d,"THE LIBRARY")
  for i,(label,t) in enumerate([("Movies",1),("TV series",2),("TV episodes",4),("Music tracks",10)]):card(d,320+i*173,label,f'{data["library"].get(str(t),0):,}')
  if data.get("library_size_label"):draw_text(d,60,1040,data["library_size_label"]+" OF MEDIA",p["accent"],42,True)
  draw_text(d,60,1130,"ADDED THIS YEAR",p["secondary"],28,True)
  draw_text(d,60,1190,f'{data["added"].get("1",0)} movies / {data["added"].get("2",0)} series / {data["added"].get("4",0)} episodes',p["fg"],27)
 page(4,library)
 def ending(d):
  draw_text(d,60,85,name.upper(),p["secondary"],34,True)
  draw_text(d,60,345,"THANK YOU",p["accent"],106,True)
  draw_text(d,60,520,"FOR WATCHING",p["fg"],71,True)
  if cta=="donation":
   msg=cta_text or "Thanks for your support. Help keep it going next year!"
   foot="PayPal, Zelle, or DM for details"
  elif cta=="thanks":
   msg=cta_text or "You made this year special."
   foot="See you next year."
  else:
   msg=cta_text or "Another great year of movies, shows and music."
   foot="See you next year."
  draw_text(d,60,805,msg,p["fg"],34,False)
  draw_text(d,60,950,foot,p["secondary"],32)
  draw_text(d,60,1210,"POWERED BY THE COMMUNITY",p["accent"],26,True)
 page(5,ending)

def main():
 ap=argparse.ArgumentParser(description="Local Plex Rewind PNG slide generator")
 sub=ap.add_subparsers(dest="command",required=True)
 x=sub.add_parser("extract");x.add_argument("--db",required=True);x.add_argument("--year",type=int,required=True);x.add_argument("--out",default="stats.json")
 r=sub.add_parser("render");r.add_argument("--data",required=True);r.add_argument("--out",default="output");r.add_argument("--name",default="My Media Server");r.add_argument("--theme",choices=THEMES,default="odyssey");r.add_argument("--cta",choices=["none","thanks","donation"],default="none");r.add_argument("--cta-text")
 a=ap.parse_args()
 if a.command=="extract":
  data=extract(a.db,a.year);Path(a.out).write_text(json.dumps(data,indent=2));print("Saved",a.out)
 else:
  render(json.loads(Path(a.data).read_text()),a.out,a.name,a.theme,a.cta,a.cta_text);print("Saved 5 slides in",a.out)
if __name__=="__main__":main()
