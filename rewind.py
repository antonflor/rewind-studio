#!/usr/bin/env python3
"""Plex year-in-review: extract aggregate metrics and render slides, an infographic or a video.

Two renderers share the same stats file:
  classic  Pillow, no extra dependencies (default; --theme picks colors and labels)
  studio   designed HTML styles rendered in headless Chromium (--style NAME; see studio/)
"""
import argparse, json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont, ImageColor

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
 "through":datetime.fromtimestamp(scalar("SELECT MAX(viewed_at) "+base) or b-1,timezone.utc).strftime("%b %d, %Y"),
 "library_size_label":None}
 for key,kind,field in [("top_movies",1,"title"),("top_shows",4,"grandparent_title")]:
  data[key]=[{"title":title or "Unknown","plays":n} for title,n in query(db,
  f"SELECT {field},COUNT(*) FROM metadata_item_views WHERE metadata_type=? AND viewed_at>=? AND viewed_at<? GROUP BY {field} ORDER BY COUNT(*) DESC,{field} LIMIT 3",(kind,a,b))]
 plays_by_month=dict(query(db,"SELECT CAST(strftime('%m',viewed_at,'unixepoch') AS INTEGER),COUNT(*) "+base+" GROUP BY 1",(a,b)))
 hours_by_month=dict(query(db,"SELECT CAST(strftime('%m',at,'unixepoch') AS INTEGER),SUM(duration)/3600.0 FROM statistics_media WHERE timespan=1 AND at>=? AND at<? GROUP BY 1",(a,b)))
 data["monthly"]=[{"month":m,"plays":plays_by_month.get(m,0),"hours":round(hours_by_month.get(m) or 0,1)} for m in range(1,13) if plays_by_month.get(m) or hours_by_month.get(m)]
 if data["monthly"]:
  top=max(data["monthly"],key=lambda r:r["plays"])
  if top["plays"]:data["busiest_month"]=dict(top)
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
def load_template(spec):
 """Load trusted local JSON data, not executable Python theme plugins."""
 if spec in THEMES:
  return dict(THEMES[spec]), {}, None
 path=Path(spec).expanduser()
 if not path.is_file():
  path=Path("templates") / (spec if spec.endswith(".json") else spec+".json")
 if not path.is_file():raise SystemExit(f"Template not found: {spec}. Run 'python rewind.py templates' to list choices.")
 obj=json.loads(path.read_text(encoding="utf-8"))
 base=THEMES.get(obj.get("extends","odyssey"))
 if base is None:raise SystemExit("Unknown base theme")
 colors=dict(base)
 for k,v in obj.get("colors",{}).items():
  if k not in colors:raise SystemExit(f"Unknown template color: {k}")
  try:ImageColor.getrgb(v)
  except ValueError:raise SystemExit(f"Invalid color: {v}")
  colors[k]=v
 return colors,obj.get("labels",{}),path.parent / obj["background"] if obj.get("background") else None

def render(data,out,name,theme,cta,cta_text,cta_methods=None):
 p,labels,bg_path=load_template(theme)
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 def label(k,default):return labels.get(k,default)
 def blank():
  img=Image.new("RGB",SIZE,p["bg"])
  if bg_path:
   if not bg_path.is_file():raise SystemExit(f"Template background does not exist: {bg_path}")
   with Image.open(bg_path) as source:
    from PIL import ImageOps
    img=Image.blend(img,ImageOps.fit(source.convert("RGB"),SIZE),0.25)
  d=ImageDraw.Draw(img)
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
  draw_text(d,60,365,label("cover_title","REWIND"),p["fg"],122,True)
  draw_text(d,60,515,str(data["year"]),p["accent"],165,True)
  draw_text(d,60,800,label("cover_subtitle","YOUR YEAR IN STREAMING"),p["secondary"],36,True)
  draw_text(d,60,1155,label("cover_footer","A year powered by the community."),p["fg"],30)
 page(1,cover)
 def stats(d):
  heading(d,label("stats_title","BY THE NUMBERS"))
  for i,(name_,value) in enumerate([("Viewer accounts",f'{data["viewers"]:,}'),("Playback events",f'{data["plays"]:,}'),("Estimated streaming hours",f'{data["hours"]:,.0f}'),("Plex media traffic",f'{data["tib"]:.2f} TiB')]):card(d,342+i*189,name_,value)
  draw_text(d,60,1190,"Playbacks are not necessarily completed watches.",p["secondary"],22)
 page(2,stats)
 def shows(d):
  heading(d,label("titles_title","MOST PLAYED"))
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
  heading(d,label("library_title","THE LIBRARY"))
  for i,(name_,t) in enumerate([("Movies",1),("TV series",2),("TV episodes",4),("Music tracks",10)]):card(d,320+i*173,name_,f'{data["library"].get(str(t),0):,}')
  if data.get("library_size_label"):draw_text(d,60,1040,data["library_size_label"]+" OF MEDIA",p["accent"],42,True)
  draw_text(d,60,1130,"ADDED THIS YEAR",p["secondary"],28,True)
  draw_text(d,60,1190,f'{data["added"].get("1",0)} movies / {data["added"].get("2",0)} series / {data["added"].get("4",0)} episodes',p["fg"],27)
 page(4,library)
 def ending(d):
  draw_text(d,60,85,name.upper(),p["secondary"],34,True)
  draw_text(d,60,345,label("closing_title","THANK YOU"),p["accent"],106,True)
  draw_text(d,60,520,label("closing_subtitle","FOR WATCHING"),p["fg"],71,True)
  if cta=="donation":
   msg=cta_text or "Thanks for your support. Help keep it going next year!"
   foot=(cta_methods.replace(" / ",", ") if cta_methods else "PayPal, Zelle, or DM")+" for details"
  elif cta=="thanks":
   msg=cta_text or "You made this year special."
   foot="See you next year."
  else:
   msg=cta_text or "Another great year of movies, shows and music."
   foot="See you next year."
  draw_text(d,60,805,msg,p["fg"],34,False)
  draw_text(d,60,950,foot,p["secondary"],32)
  draw_text(d,60,1210,label("closing_footer","POWERED BY THE COMMUNITY"),p["accent"],26,True)
 page(5,ending)


def render_infographic(data,out,name,theme,cta,cta_text,cta_methods=None):
 """Render one portrait 4:5 overview from the same aggregate data and theme."""
 from PIL import ImageOps
 colors,labels,bg_path=load_template(theme)
 p=colors
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 im=Image.new("RGB",SIZE,p["bg"])
 if bg_path:
  with Image.open(bg_path) as source:
   im=Image.blend(im,ImageOps.fit(source.convert("RGB"),SIZE),0.15)
 d=ImageDraw.Draw(im)
 W,H=SIZE
 def tx(x,y,txt,size=30,color=None,bold=False,maxwidth=940):
  draw_text(d,x,y,str(txt),color or p["fg"],size,bold,maxwidth)
 def card(x,y,w,h):
  d.rounded_rectangle((x,y,x+w,y+h),radius=22,fill=p["panel"],outline="#344951",width=2)
 def stat(x,y,w,label,value):
  card(x,y,w,158)
  tx(x+22,y+21,label.upper(),22,p["secondary"],True,w-44)
  tx(x+22,y+64,value,61,p["fg"],True,w-44)
 def rule(y):
  d.line((65,y,1015,y),fill=p["secondary"],width=2)
 d.rectangle((0,0,1080,11),fill=p["accent"])
 tx(65,49,name.upper(),36,p["secondary"],True)
 tx(65,111,labels.get("cover_title","REWIND")+" "+str(data["year"]),79,p["accent"],True)
 tx(66,218,"YOUR YEAR IN STREAMING  /  THROUGH "+data.get("through","").upper(),22,p["secondary"])
 rule(264)
 stat(65,300,460,"Viewer accounts",f'{data.get("viewers",0):,}')
 stat(555,300,460,"Playback events",f'{data.get("plays",0):,}')
 stat(65,480,460,"Estimated streaming hours",f'{data.get("hours",0):,.0f}')
 stat(555,480,460,"Plex media traffic",f'{data.get("tib",0):,.2f} TiB')
 tx(65,687,labels.get("titles_title","MOST PLAYED"),35,p["accent"],True)
 card(65,749,460,248);card(555,749,460,248)
 tx(88,771,"TOP TV SHOWS",22,p["secondary"],True)
 tx(578,771,"TOP MOVIES",22,p["secondary"],True)
 for x,key in [(88,"top_shows"),(578,"top_movies")]:
  for i,item in enumerate(data.get(key,[])[:3]):
   y=814+i*58
   tx(x,y,f'{i+1}. {item.get("title","Unknown")}',24,p["fg"],True,390)
   tx(x,y+29,str(item.get("plays",0))+" plays",17,p["secondary"])
 tx(65,1035,labels.get("library_title","THE LIBRARY"),35,p["accent"],True)
 lib=data.get("library",{})
 tx(65,1101,f'{lib.get("1",0):,} movies   •   {lib.get("2",0):,} series   •   {lib.get("4",0):,} episodes',27,p["fg"],True)
 message=(cta_text or "Help keep it going next year!") if cta=="donation" else ("Thanks for an amazing year!" if cta=="thanks" else "Your server. Your story.")
 d.rounded_rectangle((65,1170,1015,1264),radius=20,fill=p["panel"],outline=p["accent"],width=2)
 tx(88,1188,message,28,p["accent"],True,910)
 if cta=="donation":tx(88,1227,(cta_methods or "PayPal / Zelle / DM").upper().replace(" / ","  /  "),20,p["secondary"],True)
 else:tx(88,1227,"THANKS FOR WATCHING",20,p["secondary"])
 tx(65,1296,"Playback events may include partial watches. Statistics reflect a database snapshot.",17,p["secondary"])
 path=out/"infographic.png"
 im.save(path)
 return path

def main():
 ap=argparse.ArgumentParser(description="Local Plex Rewind PNG slide generator")
 sub=ap.add_subparsers(dest="command",required=True)
 x=sub.add_parser("extract");x.add_argument("--db",required=True);x.add_argument("--year",type=int,required=True);x.add_argument("--out",default="stats.json")
 r=sub.add_parser("render");r.add_argument("--data",required=True);r.add_argument("--out",default="output");r.add_argument("--name",default="My Media Server")
 r.add_argument("--theme",help="Built-in theme, template name, or path to a template JSON (classic default: odyssey; with --style it overrides the style's colors)")
 r.add_argument("--style",help="Designed studio style (run 'python rewind.py styles'); needs requirements-studio.txt")
 r.add_argument("--cta",choices=["none","thanks","donation"],default="none");r.add_argument("--cta-text")
 r.add_argument("--cta-methods",help='How to donate, slash-separated, e.g. "Ko-fi / Venmo / Ask me" (default: "PayPal / Zelle / DM")')
 r.add_argument("--format",choices=["slides","infographic","both","video","all"],default="slides",help="slides, infographic, both, or (with --style) video / all")
 r.add_argument("--no-sound",action="store_true",help="Studio video without the sound bed")
 sub.add_parser("templates",help="List built-in and local template files")
 sub.add_parser("styles",help="List designed studio styles")
 a=ap.parse_args()
 if a.command=="templates":
  print("Built-in: "+", ".join(THEMES))
  for f in sorted(Path("templates").glob("*.json")):print("Custom:",f)
  return
 if a.command=="styles":
  from studio import engine
  for s in engine.list_styles():print(f'{s["id"]:<12} {s.get("description","")}')
  return
 if a.command=="extract":
  data=extract(a.db,a.year);Path(a.out).write_text(json.dumps(data,indent=2));print("Saved",a.out)
 else:
  data=json.loads(Path(a.data).read_text())
  if a.style:
   from studio import engine
   formats={"slides":["slides"],"infographic":["infographic"],"both":["slides","infographic"],"video":["video"],"all":["slides","infographic","video"]}[a.format]
   colors,labels=None,{}
   if a.theme:colors,labels,_=load_template(a.theme)
   if a.cta_methods:labels=dict(labels,cta_methods=a.cta_methods)
   for path in engine.render(data,a.out,a.name,a.style,formats,a.cta,a.cta_text,colors,labels,sound=not a.no_sound):print("Saved",path)
   return
  if a.format in ("video","all"):raise SystemExit("Video export uses the studio engine: add --style (run 'python rewind.py styles').")
  a.theme=a.theme or "odyssey"
  if a.format in ("slides","both"):
   render(data,a.out,a.name,a.theme,a.cta,a.cta_text,a.cta_methods)
   print("Saved 5 slides in",a.out)
  if a.format in ("infographic","both"):
   path=render_infographic(data,a.out,a.name,a.theme,a.cta,a.cta_text,a.cta_methods)
   print("Saved infographic:",path)
if __name__=="__main__":main()
