from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import swisseph as swe
import math

app=Flask(__name__)
geo=Nominatim(user_agent='jyotish-kundli-final-2026')
tf=TimezoneFinder()
SIGNS=['Mesha','Vrishabha','Mithuna','Karka','Simha','Kanya','Tula','Vrishchika','Dhanu','Makara','Kumbha','Meena']
SIGN_HI=['मेष','वृषभ','मिथुन','कर्क','सिंह','कन्या','तुला','वृश्चिक','धनु','मकर','कुंभ','मीन']
NAK=['Ashwini','Bharani','Krittika','Rohini','Mrigashira','Ardra','Punarvasu','Pushya','Ashlesha','Magha','Purva Phalguni','Uttara Phalguni','Hasta','Chitra','Swati','Vishakha','Anuradha','Jyeshtha','Mula','Purva Ashadha','Uttara Ashadha','Dhanishtha','Shatabhisha','Purva Bhadrapada','Uttara Bhadrapada','Revati']
NAK_LORD=['Ketu','Venus','Sun','Moon','Mars','Rahu','Jupiter','Saturn','Mercury']*3
PLANETS=[('Sun',swe.SUN),('Moon',swe.MOON),('Mars',swe.MARS),('Mercury',swe.MERCURY),('Jupiter',swe.JUPITER),('Venus',swe.VENUS),('Saturn',swe.SATURN),('Rahu',swe.MEAN_NODE)]
PL_LORD={'Sun':0,'Moon':1,'Mars':2,'Mercury':5,'Jupiter':4,'Venus':6,'Saturn':9,'Rahu':None,'Ketu':None}
EXALT={'Sun':0,'Moon':1,'Mars':9,'Mercury':5,'Jupiter':3,'Venus':11,'Saturn':6}
DEBIL={'Sun':6,'Moon':7,'Mars':3,'Mercury':11,'Jupiter':9,'Venus':5,'Saturn':0}
OWN={0:['Sun'],1:['Venus'],2:['Mercury'],3:['Moon'],4:['Sun'],5:['Mercury'],6:['Venus'],7:['Mars'],8:['Jupiter'],9:['Saturn'],10:['Saturn'],11:['Jupiter']}
DASHA_SEQ=[('Ketu',7),('Venus',20),('Sun',6),('Moon',10),('Mars',7),('Rahu',18),('Jupiter',16),('Saturn',19),('Mercury',17)]

def norm(x): return x%360
def sign_idx(x): return int(norm(x)//30)
def sign_name(x): return SIGNS[sign_idx(x)]
def nak_info(x):
    u=norm(x)/(360/27); i=int(u); frac=u-i
    return NAK[i], i%9, min(4,int(frac*4)+1), NAK_LORD[i]
def navamsa_idx(x):
    s=sign_idx(x); part=int((norm(x)%30)/(30/9))
    # movable starts Aries, fixed starts 9 signs later, dual starts 5 signs later
    start=s if s in [0,3,6,9] else ((s+8)%12 if s in [1,4,7,10] else (s+4)%12)
    return (start+part)%12
def navamsa(x): return SIGNS[navamsa_idx(x)]
def house_from(planet_lon, asc_lon): return ((sign_idx(planet_lon)-sign_idx(asc_lon))%12)+1
def angular_diff(a,b):
    d=abs(norm(a)-norm(b)); return min(d,360-d)
def format_dt(dt): return dt.strftime('%d %b %Y %H:%M')

def status(name,lon):
    s=sign_idx(lon)
    if name in EXALT and s==EXALT[name]: return 'Exalted'
    if name in DEBIL and s==DEBIL[name]: return 'Debilitated'
    if name in ('Rahu','Ketu'): return 'Node'
    if name in OWN and name in OWN[s]: return 'Own sign'
    return 'Neutral/Friendly'

def d9_house(lon, asc): return house_from(navamsa_idx(lon)*30+15, navamsa_idx(asc)*30+15)

def graha_aspects(p):
    h=p['house']; out=[((h)%12)+1] # 7th
    if p['name']=='Mars': out += [((h+3)%12)+1,((h+7)%12)+1]
    elif p['name']=='Jupiter': out += [((h+4)%12)+1,((h+8)%12)+1]
    elif p['name']=='Saturn': out += [((h+2)%12)+1,((h+9)%12)+1]
    return sorted(set(out))

def house_lords(asc_sign):
    # sign lord index by sign
    lords=['Sun','Venus','Mercury','Moon','Sun','Mercury','Venus','Mars','Jupiter','Saturn','Saturn','Jupiter']
    return {h:lords[(asc_sign+h-1)%12] for h in range(1,13)}

def exact_vimshottari(moon_lon, birth_utc):
    nak_len=360/27
    pos=norm(moon_lon)/nak_len; nak_i=int(pos); frac=pos-nak_i
    start_lord=NAK_LORD[nak_i]
    seq_names=[x[0] for x in DASHA_SEQ]; durations=dict(DASHA_SEQ)
    start_i=seq_names.index(start_lord)
    remaining_years=durations[start_lord]*(1-frac)
    # Vimshottari year convention: 365.2425 days
    year_days=365.2425
    cur=birth_utc
    periods=[]
    # birth balance then complete cycle(s) for 120 years
    idx=start_i; first=True
    for _ in range(20):
        lord=seq_names[idx]; years=remaining_years if first else durations[lord]
        end=cur+timedelta(days=years*year_days)
        periods.append({'lord':lord,'start':cur.isoformat(),'end':end.isoformat(),'start_text':format_dt(cur),'end_text':format_dt(end),'years':round(years,4),'birth_balance':first})
        cur=end; idx=(idx+1)%9; first=False
        if (cur-birth_utc).days>120*365: break
    # antardasha for each MD, first 9 years scale proportionally; calculate all AD within first ~120 years
    for md in periods:
        md_lord=md['lord']; md_start=datetime.fromisoformat(md['start']); md_end=datetime.fromisoformat(md['end'])
        mi=seq_names.index(md_lord); ad=[]; adcur=md_start
        for j in range(9):
            lord=seq_names[(mi+j)%9]; days=(md['years']*durations[lord]/120)*year_days
            ade=adcur+timedelta(days=days)
            if ade>md_end: ade=md_end
            ad.append({'lord':lord,'start':adcur.isoformat(),'end':ade.isoformat(),'start_text':format_dt(adcur),'end_text':format_dt(ade)})
            adcur=ade
        md['antardasha']=ad
    return {'nakshatra_lord':start_lord,'nakshatra_fraction':frac,'periods':periods}

def yogas(P, asc_sign, lords):
    by={p['name']:p for p in P}; houses={h:[] for h in range(1,13)}
    for p in P: houses[p['house']].append(p['name'])
    flags=[]
    # standard named combinations, clearly flagged as traditional checks
    if 'Sun' in houses[10] and 'Mercury' in houses[10] and angular_diff(by['Sun']['longitude'],by['Mercury']['longitude'])<=12:
        flags.append(('Budhaditya Yoga','Sun + Mercury conjunction in 10th; traditional rule check.'))
    if 'Jupiter' in houses[1] and 'Moon' in houses[1] and angular_diff(by['Jupiter']['longitude'],by['Moon']['longitude'])<=12:
        flags.append(('Gajakesari-style conjunction','Moon-Jupiter conjunction in a kendra; classical variants differ.'))
    if 'Moon' in houses[2] and 'Mars' in houses[2]: flags.append(('Chandra-Mangal','Moon and Mars in 2nd; one traditional variant.'))
    if lords[1]==lords[5] or lords[1]==lords[9] or lords[5]==lords[9]:
        flags.append(('Dharma/Trikona lord connection','Lords of key trinal houses share a lord; exact Raj Yoga requires full strength/aspect assessment.'))
    # Vipreet Raj Yoga: 6/8/12 lords placed in another dusthana
    dust={6,8,12}
    for h in [6,8,12]:
        lh=lords[h]
        if by.get(lh,{}).get('house') in dust: flags.append((f'Vipreet Raj Yoga check ({h}th lord)','Dusthana lord placed in another dusthana; traditional check.'))
    return flags

def mangal(P):
    m=next(p for p in P if p['name']=='Mars'); h=m['house']
    return {'flag':h in [1,2,4,7,8,12],'house':h,'note':'Traditional Mangal Dosha screening; cancellation/strength rules require full chart assessment.'}

def predictions(P,asc,lords):
    houses={i:[] for i in range(1,13)}
    for p in P: houses[p['house']].append(p['name'])
    marriage=[]; career=[]; finance=[]
    sevenlord=lords[7]; tenlord=lords[10]; twolord=lords[2]; eleven=lords[11]
    marriage.append(f'7th house lord: {sevenlord}; detailed marriage reading should combine 7th house, 7th lord, Venus/Jupiter, D9 and running Dasha.')
    if houses[7]: marriage.append('7th house contains: '+', '.join(houses[7])+'. These planets are traditionally given extra weight in partnership interpretation.')
    if houses[5]: marriage.append('5th house contains: '+', '.join(houses[5])+', relevant to romance/children in traditional Jyotish.')
    if sevenlord in [p['name'] for p in P]:
        sl=next(p for p in P if p['name']==sevenlord); marriage.append(f'{sevenlord}, lord of the 7th, is placed in house {sl["house"]} ({sl["sign"]}); this is a primary relationship factor.')
    career.append(f'10th house lord: {tenlord}. Traditional career analysis combines the 10th house, its lord, Saturn, Sun, Mercury and Dasha.')
    if houses[10]: career.append('10th house contains: '+', '.join(houses[10])+'.')
    career.append('6th/10th/11th house links are useful for service, profession and gains; exact strength and Dasha timing are required.')
    finance.append(f'2nd lord: {twolord}; 11th lord: {eleven}. These are primary wealth/income factors in traditional Jyotish.')
    if houses[2]: finance.append('2nd house: '+', '.join(houses[2])+'.')
    if houses[11]: finance.append('11th house: '+', '.join(houses[11])+'.')
    finance.append('Long-term financial timing should be checked through 2nd/11th lords, Jupiter, Venus and Dasha/transits.')
    return {'marriage':marriage,'career':career,'finance':finance}

def compute(x):
    loc=geo.geocode(x['place'],exactly_one=True)
    if not loc: raise ValueError('Birth place not found. Try: City, State, Country')
    lat,lon=loc.latitude,loc.longitude; tz=tf.timezone_at(lat=lat,lng=lon) or 'Asia/Kolkata'
    local=datetime.fromisoformat(x['date']+'T'+x['time']).replace(tzinfo=ZoneInfo(tz)); utc=local.astimezone(ZoneInfo('UTC'))
    jd=swe.julday(utc.year,utc.month,utc.day,utc.hour+utc.minute/60+utc.second/3600)
    swe.set_sid_mode(swe.SIDM_LAHIRI); flags=swe.FLG_SWIEPH|swe.FLG_SIDEREAL|swe.FLG_SPEED
    cusps,ascmc=swe.houses_ex(jd,lat,lon,b'W',flags); asc=norm(ascmc[0]); asc_sign=sign_idx(asc); lords=house_lords(asc_sign)
    P=[]
    for n,b in PLANETS:
        q,_=swe.calc_ut(jd,b,flags); lo=norm(q[0]); nk,_,pa,nkl=nak_info(lo)
        P.append({'name':n,'longitude':lo,'sign':sign_name(lo),'sign_hi':SIGN_HI[sign_idx(lo)],'degree':round(lo%30,4),'house':house_from(lo,asc),'nakshatra':nk,'pada':pa,'nakshatra_lord':nkl,'navamsa':navamsa(lo),'navamsa_house':d9_house(lo,asc),'retrograde':q[3]<0,'status':status(n,lo)})
    rahu=next(p for p in P if p['name']=='Rahu'); lo=norm(rahu['longitude']+180); nk,_,pa,nkl=nak_info(lo)
    P.append({'name':'Ketu','longitude':lo,'sign':sign_name(lo),'sign_hi':SIGN_HI[sign_idx(lo)],'degree':round(lo%30,4),'house':house_from(lo,asc),'nakshatra':nk,'pada':pa,'nakshatra_lord':nkl,'navamsa':navamsa(lo),'navamsa_house':d9_house(lo,asc),'retrograde':False,'status':'Node'})
    for p in P: p['aspects']=graha_aspects(p)
    moon=next(p for p in P if p['name']=='Moon')
    dash=exact_vimshottari(moon['longitude'],utc)
    ys=yogas(P,asc_sign,lords); mg=mangal(P); pred=predictions(P,asc,lords)
    # D9 asc and planets are represented through navamsa sign + house
    d9planets=[{'name':p['name'],'sign':p['navamsa'],'house':p['navamsa_house']} for p in P]
    return {'name':x.get('name',''),'gender':x.get('gender',''),'birth':{'place':loc.address,'lat':lat,'lon':lon,'timezone':tz,'local_time':local.isoformat(),'utc_time':utc.isoformat()},'lagna':{'sign':sign_name(asc),'sign_hi':SIGN_HI[asc_sign],'degree':round(asc%30,4),'longitude':asc,'navamsa':navamsa(asc)},'rashi':moon['sign'],'rashi_hi':moon['sign_hi'],'nakshatra':moon['nakshatra'],'nakshatra_lord':moon['nakshatra_lord'],'planets':P,'house_lords':lords,'yogas':ys,'mangal':mg,'pred':pred,'dasha':dash,'d9planets':d9planets,'generated_at':datetime.now().isoformat()}

@app.post('/api/kundli')
def api():
    try: return jsonify(ok=True,data=compute(request.json))
    except Exception as e: return jsonify(ok=False,error=str(e)),400
@app.route('/')
def home(): return render_template('index.html')

if __name__=='__main__': app.run(host='0.0.0.0',port=5000,debug=True)
