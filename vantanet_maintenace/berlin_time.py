"""Europe/Berlin timezone with an EU-rule fallback for minimal test hosts."""
import calendar
from datetime import datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class _BerlinFallback(tzinfo):
    standard=timedelta(hours=1)
    daylight=timedelta(hours=2)

    @staticmethod
    def _last_sunday(year,month):
        day=calendar.monthrange(year,month)[1]
        while datetime(year,month,day).weekday()!=6:day-=1
        return day

    def _local_transitions(self,year):
        start=datetime(year,3,self._last_sunday(year,3),2)
        end=datetime(year,10,self._last_sunday(year,10),3)
        return start,end

    def utcoffset(self,dt):
        if dt is None:return self.standard
        local=dt.replace(tzinfo=None);start,end=self._local_transitions(local.year)
        if start<=local<start+timedelta(hours=1):
            return self.daylight if dt.fold else self.standard
        if end-timedelta(hours=1)<=local<end:
            return self.standard if dt.fold else self.daylight
        return self.daylight if start+timedelta(hours=1)<=local<end else self.standard

    def dst(self,dt):return self.utcoffset(dt)-self.standard
    def tzname(self,dt):return 'CEST' if self.dst(dt) else 'CET'

    def fromutc(self,dt):
        utc=dt.replace(tzinfo=None)
        march=self._last_sunday(utc.year,3);october=self._last_sunday(utc.year,10)
        start=datetime(utc.year,3,march,1);end=datetime(utc.year,10,october,1)
        daylight=start<=utc<end
        local=utc+(self.daylight if daylight else self.standard)
        fold=1 if end<=utc<end+timedelta(hours=1) else 0
        return local.replace(tzinfo=self,fold=fold)


try:BERLIN=ZoneInfo('Europe/Berlin')
except ZoneInfoNotFoundError:BERLIN=_BerlinFallback()
