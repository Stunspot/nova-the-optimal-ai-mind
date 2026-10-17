"""Fixed Windows observation v1. No command runner, scanner or configuration writer."""
import ctypes,datetime,hashlib,json,os,sys,time
from ctypes import wintypes as W
METHOD='windows-bounded-observation/v1'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')
def unavailable(reason):return {'state':'unavailable','reason':reason}
def cpu_percent(before,after):
 d=[b-a for a,b in zip(before,after)];total=d[1]+d[2]
 if min(d)<0 or total<=0 or d[0]>total:raise ValueError('CPU timing counters reset or did not advance. Try another observation.')
 return 100*(total-d[0])/total

def power_values(ac,flags,percent):
 battery='unknown' if flags==255 else 'no system battery' if flags&128 else 'charging' if flags&8 else 'not charging'
 return {'state':'available','ac':{0:'offline',1:'online'}.get(ac,'unknown'),'battery':battery,'percent':percent if flags!=255 and not flags&128 and 0<=percent<=100 else None}
class Windows:
 def __init__(self):
  if os.name!='nt':raise OSError('This fixed observation uses Windows APIs. Prepared investigations and selected sources remain readable on this platform.')
  self.k=ctypes.WinDLL('kernel32',use_last_error=True)
  self.k.GetSystemTimes.argtypes=[ctypes.POINTER(W.FILETIME)]*3;self.k.GetSystemTimes.restype=W.BOOL
  self.k.GetActiveProcessorGroupCount.argtypes=[];self.k.GetActiveProcessorGroupCount.restype=W.WORD
  self.k.GetComputerNameW.argtypes=[W.LPWSTR,ctypes.POINTER(W.DWORD)];self.k.GetComputerNameW.restype=W.BOOL
  self.k.GetSystemDirectoryW.argtypes=[W.LPWSTR,W.UINT];self.k.GetSystemDirectoryW.restype=W.UINT
  self.k.GetVolumePathNameW.argtypes=[W.LPCWSTR,W.LPWSTR,W.DWORD];self.k.GetVolumePathNameW.restype=W.BOOL
  self.k.GetDiskFreeSpaceExW.argtypes=[W.LPCWSTR]+[ctypes.POINTER(ctypes.c_ulonglong)]*3;self.k.GetDiskFreeSpaceExW.restype=W.BOOL
 def check(self,value):
  if not value:raise OSError('Windows could not provide this measure (error '+str(ctypes.get_last_error())+'). Try another observation; do not treat it as zero.')
 def machine(self):
  b=ctypes.create_unicode_buffer(256);n=W.DWORD(len(b));self.check(self.k.GetComputerNameW(b,ctypes.byref(n)))
  return hashlib.sha256(('beryl-local-name-v1:'+b.value.casefold()).encode()).hexdigest()
 def times(self):
  groups=self.k.GetActiveProcessorGroupCount()
  if groups!=1:raise ValueError('Whole-PC CPU comparison is unavailable on multiple or unknown processor groups; GetSystemTimes would cover only one group.')
  values=[W.FILETIME() for _ in range(3)];self.check(self.k.GetSystemTimes(*[ctypes.byref(v) for v in values]));return [v.dwLowDateTime+(v.dwHighDateTime<<32) for v in values]
 def memory(self):
  class Memory(ctypes.Structure):_fields_=[('length',W.DWORD),('load',W.DWORD)]+[(n,ctypes.c_ulonglong) for n in ['total','available','page_total','page_available','virtual_total','virtual_available','extended']]
  self.k.GlobalMemoryStatusEx.argtypes=[ctypes.POINTER(Memory)];self.k.GlobalMemoryStatusEx.restype=W.BOOL
  m=Memory();m.length=ctypes.sizeof(m);self.check(self.k.GlobalMemoryStatusEx(ctypes.byref(m)))
  return {'state':'available','total_bytes':m.total,'available_bytes':m.available}
 def disk(self):
  b=ctypes.create_unicode_buffer(32768);n=self.k.GetSystemDirectoryW(b,len(b));self.check(n)
  if n>=len(b):raise ValueError('Windows system directory exceeds the supported buffer.')
  root=ctypes.create_unicode_buffer(32768);self.check(self.k.GetVolumePathNameW(b.value,root,len(root)))
  a,t,f=[ctypes.c_ulonglong() for _ in range(3)];self.check(self.k.GetDiskFreeSpaceExW(root.value,ctypes.byref(a),ctypes.byref(t),ctypes.byref(f)))
  return {'state':'available','volume':root.value,'available_to_account_bytes':a.value,'total_for_account_bytes':t.value,'volume_free_bytes':f.value}
 def power(self):
  class Power(ctypes.Structure):_fields_=[(n,W.BYTE) for n in ['ac','flags','percent','saver']]+[('life',W.DWORD),('full',W.DWORD)]
  self.k.GetSystemPowerStatus.argtypes=[ctypes.POINTER(Power)];self.k.GetSystemPowerStatus.restype=W.BOOL
  p=Power();self.check(self.k.GetSystemPowerStatus(ctypes.byref(p)));return power_values(p.ac,p.flags,p.percent)

def capture(api=None,sleeper=time.sleep):
 result={'method':METHOD,'started_at':utc(),'platform':sys.platform,'machine_id':None,'identity_note':'Hash of this Windows computer name, not a hardware identity. Rename or duplicate computer names limit comparison.'}
 try:api=api or Windows()
 except (OSError,ValueError) as e:
  result.update({k:unavailable(str(e)) for k in ['cpu','memory','disk','power']});result['ended_at']=utc();result['seconds']=0;return result
 try:result['machine_id']=api.machine()
 except (OSError,ValueError) as e:result['identity_error']=str(e)
 before=None
 try:before=api.times()
 except (OSError,ValueError) as e:result['cpu']=unavailable(str(e))
 start=time.monotonic();sleeper(3);result['seconds']=round(time.monotonic()-start,3)
 if before is not None:
  try:result['cpu']={'state':'available','busy_percent':round(cpu_percent(before,api.times()),3),'scope':'All processors in the single active Windows processor group','interval_seconds':result['seconds']}
  except (OSError,ValueError) as e:result['cpu']=unavailable(str(e))
 for field in ['memory','disk','power']:
  try:result[field]=getattr(api,field)()
  except (OSError,ValueError) as e:result[field]=unavailable(str(e))
 result['ended_at']=utc();return result
if __name__=='__main__':print(json.dumps(capture(),ensure_ascii=False))
